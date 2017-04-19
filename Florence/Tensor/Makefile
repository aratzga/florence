PYTHON_VERSION = python2.7
PYTHON_INCLUDE_PATH = /usr/include/
PYTHON_LD_PATH = /usr/lib/
CYTHONFLAGS = -DNPY_NO_DEPRECATED_API -Wno-cpp -Wno-unused-function -Wno-maybe-uninitialized

CYTHON = cython --cplus
REMOVE = rm -rf

INLINE_THRESHOLD = 100000
CXXSTD=-std=c++14
OPTFLAGS= -O3 -fno-strict-aliasing -DNDEBUG
CXXFLAGS= -fPIC -shared -pthread -Wall $(CYTHONFLAGS) $(OPTFLAGS)

# NUMPY_INCLUDE_PATH=python -c "import numpy; print numpy.get_include()"
NUMPY_INCLUDE_PATH = /usr/local/lib/python2.7/dist-packages/numpy/core/include

ifeq ($(findstring g++,$(CXX)),g++)
ifneq ($(findstring clang++,$(CXX)),clang++)
CXXFLAGS += -march=native -ffast-math -fwrapv -mfpmath=sse -funroll-loops -finline-functions -finline-limit=$(INLINE_THRESHOLD) -ffp-contract=fast 
else
CXXFLAGS += -march=native -ffast-math -mllvm -inline-threshold=$(INLINE_THRESHOLD) -ffp-contract=fast
endif
endif
ifeq ($(findstring icpc,$(CXX)),icpc)
CXXFLAGS += -march=native -no-ansi-alias -xHost -fp-model fast=1 -inline-forceinline -inline-factor=$(INLINE_THRESHOLD)
endif

all: build_module

build_module: 
	@echo "Building Florence supplementary tensor numeric module"
	$(CYTHON) Numeric.pyx
	$(CXX) $(CXXSTD) $(CXXFLAGS) Numeric.cpp _Numeric.cpp -o Numeric.so -I. -I$(PYTHON_INCLUDE_PATH) -I$(NUMPY_INCLUDE_PATH) -L$(PYTHON_LD_PATH) -l$(PYTHON_VERSION)

	@echo "Building Florence supplementary tensor linear algebra module"
	$(CYTHON) LinAlg.pyx
	$(CXX) $(CXXSTD) $(CXXFLAGS) _Numeric.cpp _LinAlg.cpp LinAlg.cpp -o LinAlg.so -I. -I$(PYTHON_INCLUDE_PATH) -I$(NUMPY_INCLUDE_PATH) -L$(PYTHON_LD_PATH) -l$(PYTHON_VERSION)

clean:
	$(REMOVE) Numeric.cpp LinAlg.cpp Numeric.so LinAlg.so

source_clean:
	$(REMOVE) Numeric.cpp LinAlg.cpp