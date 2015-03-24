/*
 *
 *  Repeatedly scan with RSSI
 *
 *  Copyright (C) 2004  Scott Gifford <gifford@umich.edu>
 *  Copyright (C) 2003  Marcel Holtmann <marcel@holtmann.org>
 *
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 */

#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <sys/poll.h>
#include <stdlib.h>
#include <time.h>
#include <getopt.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <sys/time.h>

#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <netinet/in.h>

#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/hci_lib.h>

int debug = 0;

int sock;
struct sockaddr_in srv_addr;
unsigned char mac_address[6];

#define POLL_TIMEOUT 11000
#define MAX_DELAY    2000

struct status_packet {
  uint32_t timestamp_sec;
  uint32_t timestamp_usec;
  uint8_t host_mac_addr[6];
  uint8_t device_bt_addr[6];
  int8_t rssi;
} __attribute__((__packed__));

void usage(char *name)
{
  fprintf(stderr,"Usage: %s -h <host> [-p port (default 2410)] [-i hci-if]\n",name);
  exit(2);
}

static volatile sig_atomic_t __io_canceled = 0;

static void sig_hup(int sig)
{
  return;
}

static void sig_term(int sig)
{
  __io_canceled = 1;
}

static void show_inquiry_result(bdaddr_t *bdaddr, int8_t rssi)
{
  struct timeval time;
  struct status_packet pkt;
  int i;

  memset(&pkt, 0, sizeof(pkt));
  
  for (i = 0; i < 6; i++) {
    pkt.host_mac_addr[i] = (uint8_t) mac_address[i];
    pkt.device_bt_addr[i] = (uint8_t) bdaddr->b[i];	// For some reason, bdaddr->b is backwards
  }

  gettimeofday(&time, NULL);
  pkt.timestamp_sec = htonl((uint32_t) time.tv_sec);
  pkt.timestamp_usec = htonl((uint32_t) time.tv_usec);
  
  pkt.rssi = rssi;
  
  sendto(sock, (void *)(&pkt), sizeof(pkt), 0, (const struct sockaddr *)&srv_addr, sizeof(pkt));
  
  fprintf(stderr, ".");
}

static void inquiry_result(int dd, unsigned char *buf, int len)
{
  inquiry_info *info;
  uint8_t num;
  int i;

  num = buf[0];
  if (debug) fprintf(stderr,"inquiry_result:\tnum %d\n", num);

  for (i = 0; i < num; i++) {
    info = (void *) buf + (sizeof(*info) * i) + 1;
    //show_inquiry_result(&info->bdaddr, INT_MIN);  // Surpress results w/o rssi
    fprintf(stderr, "_");
  }
}

static void inquiry_result_with_rssi(int dd, unsigned char *buf, int len)
{
  inquiry_info_with_rssi *info;
  uint8_t num;
  int i;

  num = buf[0];
  if (debug) fprintf(stderr,"inquiry_result_with_rssi:\tnum %d\n", num);

  for (i = 0; i < num; i++) {
    info = (void *) buf + (sizeof(*info) * i) + 1;
    show_inquiry_result(&info->bdaddr, info->rssi);
  }
}


/* Try to active RSSI on inquiry, but if it doesn't work oh well. */
static void activate_rssi(int dd)
{
  write_inquiry_mode_cp cp;
  int err;

  cp.mode = 1;
  err = hci_send_cmd(dd, OGF_HOST_CTL, OCF_WRITE_INQUIRY_MODE, WRITE_INQUIRY_MODE_RP_SIZE, &cp);
  if (debug) fprintf(stderr,"activate_rssi: err=%d\n",err);
  /* No other error checking, since this may fail and we don't care. */
}


static void begin_inquiry(int dd)
{
  inquiry_cp cp;
  int err;

  if (debug) fprintf(stderr,"begin_inquiry: starting\n");
  memset (&cp, 0, sizeof(cp));
  cp.lap[2] = 0x9e;
  cp.lap[1] = 0x8b;
  cp.lap[0] = 0x33;
  cp.num_rsp = 0;
  cp.length = 0x30;

  err = hci_send_cmd (dd, OGF_LINK_CTL, OCF_INQUIRY,
		      INQUIRY_CP_SIZE, &cp);
  if (err < 0)
  {
    fprintf(stderr,"Error #%d beginning inquiry\n",err);
    exit(1);
  }
}

static void cancel_inquiry(int dd)
{
  int err;

  err = hci_send_cmd (dd, OGF_LINK_CTL, OCF_INQUIRY_CANCEL,
		      0, NULL);
  if (debug) fprintf(stderr,"cancel_inquiry: err=%d\n",err);
  /* No other error checking, because what would we do? */
}

int main(int argc, char *argv[])
{
  unsigned char buf[HCI_MAX_EVENT_SIZE], *ptr;
  hci_event_hdr *hdr;
  struct hci_filter flt;
  char *srv_name = "";
  int srv_port = 2410;
  struct sigaction sa;
  struct pollfd p;
  int dd = -1, dev = 0, len;
  int errflg = 0;
  int c;
  extern char *optarg;
  extern int optind;

  /* Process command-line options */
  while ((c = getopt(argc, argv, "h:p:i:")) != EOF)
  {
    switch(c)
    {
      case 'i':
        if ((dev = hci_devid(optarg)) < 0)
        {
          fprintf(stderr,"Invalid device '%s': %s\n",optarg,strerror(errno));
          exit(1);
        }
        break;
      case 'h':
        srv_name = optarg;
        break;
      case 'p':
        srv_port = atoi(optarg);
        break;
      case '?':
        errflg++;
        break;
    }
  }
  
  if (!strcmp(srv_name, ""))
    errflg++;

  if (errflg)
    usage(argv[0]);
	
  /* Open the Bluetooth device */
  dd = hci_open_dev(dev);
  if (dd < 0) {
    perror("Can't open HCI device");
    exit(1);
  }

  /* Set up an event filter; we only care about inquiry-related
   *  events.
   */
  hci_filter_clear(&flt);
  hci_filter_set_ptype(HCI_EVENT_PKT, &flt);
  //hci_filter_set_event(EVT_INQUIRY_RESULT, &flt);
  hci_filter_set_event(EVT_INQUIRY_RESULT_WITH_RSSI, &flt);
  hci_filter_set_event(EVT_INQUIRY_COMPLETE, &flt);
  if (setsockopt(dd, SOL_HCI, HCI_FILTER, &flt, sizeof(flt)) < 0) {
    perror("Can't set HCI filter");
    exit(1);
  }
  
  /* open socket */
  sock = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
  memset(&srv_addr, 0, sizeof(srv_addr));
  srv_addr.sin_family = AF_INET;
  srv_addr.sin_port = htons(srv_port);
  
  struct hostent *result = gethostbyname(srv_name);
  if (!result) {
    perror("DNS lookup failed");
    exit(1);
  }
  
  memcpy(&srv_addr.sin_addr.s_addr, result->h_addr, result->h_length);
  
  char addr[16];
  inet_ntop(AF_INET, &srv_addr.sin_addr.s_addr, addr, 16);
  fprintf(stderr, "Sending to %s:%d ", addr, srv_port);
  
  /* Get the host mac addr, shamelessly ripped from stackoverflow */
  struct ifreq ifr;
  struct ifconf ifc;
  char tmp[1024];
  int success = 0;

  int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
  if (sock == -1) {
    perror("Unable to open socket");
    exit(1);
  };

  ifc.ifc_len = sizeof(tmp);
  ifc.ifc_buf = tmp;
  if (ioctl(sock, SIOCGIFCONF, &ifc) == -1) { /* handle error */ }

  struct ifreq* it = ifc.ifc_req;
  struct ifreq* end = it + (ifc.ifc_len / sizeof(struct ifreq));

  for (; it != end; ++it) {
    strcpy(ifr.ifr_name, it->ifr_name);
    if (ioctl(sock, SIOCGIFFLAGS, &ifr) == 0) {
      if (! (ifr.ifr_flags & IFF_LOOPBACK)) { // don't count loopback
        if (ioctl(sock, SIOCGIFHWADDR, &ifr) == 0) {
          success = 1;
          break;
        }
      }
    } else { /* handle error */ }
  }
  memcpy(mac_address, ifr.ifr_hwaddr.sa_data, 6);

  /* Set up signal handlers */
  memset(&sa, 0, sizeof(sa));
  sa.sa_flags   = SA_NOCLDSTOP;
  sa.sa_handler = SIG_IGN;
  sigaction(SIGCHLD, &sa, NULL);
  sigaction(SIGPIPE, &sa, NULL);

  sa.sa_handler = sig_term;
  sigaction(SIGTERM, &sa, NULL);
  sigaction(SIGINT,  &sa, NULL);

  sa.sa_handler = sig_hup;
  sigaction(SIGHUP, &sa, NULL);

  /* Set up the random number generator, for random delays for
   * scan.  This tries to avoid multiple machines running this
   * software from starting at the same time and flooding the
   * network at the same time.
   */

  srand(time(NULL) ^ getpid());

  /* Request RSSI if available, then start the first inquiry. */
  activate_rssi(dd);
  usleep(rand() % MAX_DELAY);
  begin_inquiry(dd);

  /* Now poll for events until a signal tells us to cancel. */
  p.fd = dd;
  p.events = POLLIN | POLLERR | POLLHUP;
  while (!__io_canceled) {
    p.revents = 0;
    if (debug) fprintf(stderr,"Polling...\n");
    if (poll(&p, 1, POLL_TIMEOUT) > 0) {
      len = read(dd, buf, sizeof(buf));
      if (len < 0)
        continue;
      else if (len == 0)
        break; /* EOF */

      hdr = (void *) (buf + 1);
      ptr = buf + (1 + HCI_EVENT_HDR_SIZE);
      len -= (1 + HCI_EVENT_HDR_SIZE);
      if (debug) fprintf(stderr,"Got event!  Type is %d\n",hdr->evt);

      switch (hdr->evt) {

        case EVT_INQUIRY_RESULT:
          inquiry_result(dd, ptr, len);
          break;

        case EVT_INQUIRY_RESULT_WITH_RSSI:
          inquiry_result_with_rssi(dd, ptr, len);
          break;

        case EVT_INQUIRY_COMPLETE:
          /* Inquiry is finished, wait a random time
           * then start another. 
           */

          if (debug) fprintf(stderr,"Inquiry complete\n");
          usleep(rand() % MAX_DELAY);
          begin_inquiry(dd);
          break;
      }
    }
  }
  
  printf("\n");

  if (debug) fprintf(stderr,"Program finished.\n");

  cancel_inquiry(dd);
 
  if (hci_close_dev(dd) < 0) {
    perror("Can't close HCI device");
    exit(1);
  }

  return 0;
}
