%module NLMaP

%include "std_vector.i"
%include "carrays.i"
%array_class(float, floatArray);

%{
#include <NLMAP/MultiLateration.hh>
#include <NLMAP/Parameters.hh>
#include <NLMAP/IterativeModeler.hh>
#include <NLMAP/LaterationFunction.hh>
#include <NLMAP/LaterationSorter.hh>
%}

///
/// Struct to hold position
///
struct XYZData {
  float x;
  float y;
  float z;
  float sigma;
};


// Wrapper class for positioning
class MultiLateration {
public:
  ///
  /// Constructor
  /// @param x Array of x co-ordinates
  /// @param y Array of y co-ordinates
  /// @param z Array of z co-ordinates
  /// @param d Array of lateration measures
  /// @param sigma Array of 1-sigma errors on d
  /// @param n Size of input arrays
  ///
  MultiLateration(float x[], 
		  float y[], 
		  float z[],
		  float d[],
		  float sigma[],
		  int n);
  
  virtual ~MultiLateration();

  ///
  /// Wrapper to use iterative modeler
  /// to calculate a position
  /// @param max_it Maximum number of iterations in each NLM
  /// @param min_delta Minimum delta for NLM to stop
  /// @param convergence Accuracy sought
  /// @return The position
  ///
  XYZData GetPosition(
		      const int  max_it,
		      const float min_delta,
		      const float convergence);  

};
