mkdir build
cmake -H. -Bbuild -G "Visual Studio 17 2022"
cmake --build build/
cmake --build build/ --config Release