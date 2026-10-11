#include <dxc/dxcapi.h>

#include <cstdio>
#include <cstring>

int main()
{
    CComPtr<IDxcCompiler3> compiler;
    CComPtr<IDxcUtils> utils;
    if (FAILED(DxcCreateInstance(CLSID_DxcCompiler, IID_PPV_ARGS(&compiler))) ||
        FAILED(DxcCreateInstance(CLSID_DxcUtils, IID_PPV_ARGS(&utils))))
    {
        std::printf("DxcCreateInstance failed\n");
        return 1;
    }

    const char* source = "[numthreads(1, 1, 1)] void main() {}";
    DxcBuffer buffer = {source, std::strlen(source), DXC_CP_UTF8};
    LPCWSTR args[] = {L"-T", L"cs_6_0", L"-E", L"main", L"-spirv"};
    CComPtr<IDxcResult> result;
    if (FAILED(compiler->Compile(&buffer, args, sizeof(args) / sizeof(args[0]), nullptr, IID_PPV_ARGS(&result))))
    {
        return 1;
    }
    HRESULT status = E_FAIL;
    result->GetStatus(&status);
    CComPtr<IDxcBlob> spirv;
    result->GetOutput(DXC_OUT_OBJECT, IID_PPV_ARGS(&spirv), nullptr);
    const size_t size = spirv ? spirv->GetBufferSize() : 0;
    std::printf("Compiled a compute shader to %zu bytes of SPIR-V\n", size);
    return SUCCEEDED(status) && size > 0 ? 0 : 1;
}
