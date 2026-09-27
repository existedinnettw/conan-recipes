# Stands in for the OMSimulator-3rdParty submodule, whose libraries all come from Conan
# packages here: the oms::3rd:: targets OMSimulator links are aliases of theirs.

find_package(ctpl REQUIRED CONFIG)
find_package(lua REQUIRED CONFIG)
find_package(omsimulator-fmi4c REQUIRED CONFIG)
find_package(pugixml REQUIRED CONFIG)
find_package(sundials REQUIRED CONFIG)
find_package(XercesC REQUIRED CONFIG)
find_package(ZLIB REQUIRED CONFIG)

add_library(oms::3rd::ctpl::header ALIAS ctpl::ctpl)
add_library(oms::3rd::cvode ALIAS sundials::sundials)
add_library(oms::3rd::fmi4c ALIAS omsimulator-fmi4c::fmi4c)
add_library(oms::3rd::kinsol ALIAS sundials::sundials)
add_library(oms::3rd::lua ALIAS lua::lua)
# OMSimulator calls the miniunz()/minizip() command line functions.
add_library(oms::3rd::minizip ALIAS omsimulator-fmi4c::miniunz)
add_library(oms::3rd::pugixml::header ALIAS pugixml::pugixml)
add_library(oms::3rd::xerces ALIAS XercesC::XercesC)
add_library(oms::3rd::zlib ALIAS ZLIB::ZLIB)
