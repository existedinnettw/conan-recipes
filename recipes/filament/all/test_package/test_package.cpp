#include <filament/Engine.h>
#include <filament/Material.h>
#include <filament/Scene.h>
#include <filament/View.h>
#include <filamat/MaterialBuilder.h>
#include <gltfio/AssetLoader.h>
#include <gltfio/MaterialProvider.h>
#include <utils/EntityManager.h>

#include <cstdio>

using namespace filament;

int main() {
    // The no-op backend needs no GPU or window.
    Engine* engine = Engine::create(Engine::Backend::NOOP);

    // Compile a material at run time (filamat, with upstream's glslang and SPIRV-Tools).
    filamat::MaterialBuilder::init();
    filamat::MaterialBuilder builder;
    builder.name("red")
            .material("void material(inout MaterialInputs material) {\n"
                      "    prepareMaterial(material);\n"
                      "    material.baseColor.rgb = float3(1.0, 0.0, 0.0);\n"
                      "}\n")
            .shading(filamat::MaterialBuilder::Shading::LIT)
            .targetApi(filamat::MaterialBuilder::TargetApi::OPENGL)
            .platform(filamat::MaterialBuilder::Platform::DESKTOP);
    filamat::Package package = builder.build(engine->getJobSystem());
    filamat::MaterialBuilder::shutdown();
    if (!package.isValid()) {
        std::puts("material compilation failed");
        Engine::destroy(&engine);
        return 1;
    }

    Material* material = Material::Builder()
            .package(package.getData(), package.getSize())
            .build(*engine);
    Scene* scene = engine->createScene();
    View* view = engine->createView();
    view->setScene(scene);

    gltfio::MaterialProvider* materials = gltfio::createJitShaderProvider(engine);
    gltfio::AssetLoader* loader = gltfio::AssetLoader::create({engine, materials});

    std::printf("filament: compiled %zu-byte material '%s'\n", package.getSize(),
            material->getName());

    gltfio::AssetLoader::destroy(&loader);
    materials->destroyMaterials();
    delete materials;
    engine->destroy(view);
    engine->destroy(scene);
    engine->destroy(material);
    Engine::destroy(&engine);
    return 0;
}
