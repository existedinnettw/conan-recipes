#include <mcpp_lib.h>

#include <stdio.h>
#include <string.h>

static int g_includes = 0;

// O3DE's addition to the library API
static void report_include(FILE* fp, const char* src_dir, const char* filename, const char* fullname)
{
    (void)fp;
    (void)src_dir;
    (void)filename;
    (void)fullname;
    ++g_includes;
}

int main(void)
{
    const char* source = "test_input.h";
    FILE* f = fopen(source, "w");
    if (!f)
    {
        return 1;
    }
    fputs("#define SQUARE(x) ((x) * (x))\nint area = SQUARE(4);\n", f);
    fclose(f);

    mcpp_use_mem_buffers(1);
    mcpp_set_report_include_callback(report_include);
    const char* argv[] = {"mcpp", source};
    const int result = mcpp_lib_main(2, argv);
    const char* output = mcpp_get_mem_buffer(MCPP_OUT);
    printf("mcpp output:\n%s\n", output ? output : "(none)");
    if (result != 0 || !output || !strstr(output, "((4) * (4))"))
    {
        return 1;
    }
    return 0;
}
