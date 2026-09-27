/* Loads the FMU exported by openmodelica_add_fmu() and co-simulates it for 1 s. */
#include <dlfcn.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The few FMI 2.0 types and entry points used here, as in fmi2FunctionTypes.h. */
typedef void* fmi2Component;
typedef unsigned int fmi2ValueReference;
typedef double fmi2Real;
typedef int fmi2Boolean;
typedef int fmi2Status; /* 0 == fmi2OK */
typedef struct {
  void (*logger)(void*, const char*, fmi2Status, const char*, const char*, ...);
  void* (*allocateMemory)(size_t, size_t);
  void (*freeMemory)(void*);
  void (*stepFinished)(void*, fmi2Status);
  void* componentEnvironment;
} fmi2CallbackFunctions;

typedef const char* (*GetVersion_t)(void);
typedef fmi2Component (*Instantiate_t)(const char*, int, const char*, const char*,
                                     const fmi2CallbackFunctions*, fmi2Boolean, fmi2Boolean);
typedef fmi2Status (*SetupExperiment_t)(fmi2Component, fmi2Boolean, fmi2Real, fmi2Real, fmi2Boolean, fmi2Real);
typedef fmi2Status (*ComponentFunction_t)(fmi2Component);
typedef fmi2Status (*DoStep_t)(fmi2Component, fmi2Real, fmi2Real, fmi2Boolean);
typedef fmi2Status (*GetReal_t)(fmi2Component, const fmi2ValueReference*, size_t, fmi2Real*);
typedef void (*FreeInstance_t)(fmi2Component);

static void logger(void* env, const char* instance, fmi2Status status, const char* category,
                   const char* message, ...)
{
  va_list args;
  (void)env;
  va_start(args, message);
  fprintf(stderr, "[%s %d %s] ", instance, status, category);
  vfprintf(stderr, message, args);
  fputc('\n', stderr);
  va_end(args);
}

static char* read_file(const char* path)
{
  FILE* f = fopen(path, "rb");
  long size;
  char* text;
  if (!f)
    return NULL;
  fseek(f, 0, SEEK_END);
  size = ftell(f);
  fseek(f, 0, SEEK_SET);
  text = calloc((size_t)size + 1, 1);
  if (fread(text, 1, (size_t)size, f) != (size_t)size) {
    free(text);
    text = NULL;
  }
  fclose(f);
  return text;
}

/* Copies the value of attribute `name` from the first element after `from` into `out`. */
static int xml_attribute(const char* from, const char* name, char* out, size_t out_size)
{
  char key[64];
  const char* begin;
  const char* end;
  snprintf(key, sizeof key, " %s=\"", name);
  begin = strstr(from, key);
  if (!begin)
    return 0;
  begin += strlen(key);
  end = strchr(begin, '"');
  if (!end || (size_t)(end - begin) >= out_size)
    return 0;
  memcpy(out, begin, (size_t)(end - begin));
  out[end - begin] = '\0';
  return 1;
}

#define LOAD(type, name)                                        \
  type name = (type)dlsym(lib, "fmi2" #name);                   \
  if (!name) {                                                  \
    fprintf(stderr, "missing fmi2" #name "\n");                 \
    return 1;                                                   \
  }

int main(int argc, char** argv)
{
  char path[4096], guid[128], uri[4200], vr_text[32];
  char* description;
  const char* variable;
  fmi2ValueReference vr;
  fmi2CallbackFunctions callbacks = {logger, calloc, free, NULL, NULL};
  fmi2Component c;
  fmi2Real t = 0.0, x = 0.0;
  const fmi2Real dt = 0.01;
  void* lib;
  int i;

  if (argc != 2) {
    fprintf(stderr, "usage: %s <unpacked FMU directory>\n", argv[0]);
    return 1;
  }

  snprintf(path, sizeof path, "%s/modelDescription.xml", argv[1]);
  description = read_file(path);
  if (!description || !xml_attribute(description, "guid", guid, sizeof guid)) {
    fprintf(stderr, "cannot read the GUID from %s\n", path);
    return 1;
  }
  variable = strstr(description, " name=\"x\"");
  if (!variable || !xml_attribute(variable, "valueReference", vr_text, sizeof vr_text)) {
    fprintf(stderr, "no variable x in %s\n", path);
    return 1;
  }
  vr = (fmi2ValueReference)strtoul(vr_text, NULL, 10);

  snprintf(path, sizeof path, "%s/binaries/linux64/Decay.so", argv[1]);
  lib = dlopen(path, RTLD_NOW | RTLD_LOCAL);
  if (!lib) {
    fprintf(stderr, "%s\n", dlerror());
    return 1;
  }

  {
    LOAD(GetVersion_t, GetVersion)
    LOAD(Instantiate_t, Instantiate)
    LOAD(SetupExperiment_t, SetupExperiment)
    LOAD(ComponentFunction_t, EnterInitializationMode)
    LOAD(ComponentFunction_t, ExitInitializationMode)
    LOAD(DoStep_t, DoStep)
    LOAD(GetReal_t, GetReal)
    LOAD(ComponentFunction_t, Terminate)
    LOAD(FreeInstance_t, FreeInstance)

    printf("FMI version %s, GUID %s\n", GetVersion(), guid);
    snprintf(uri, sizeof uri, "file://%s/resources", argv[1]);
    c = Instantiate("decay", 1 /* fmi2CoSimulation */, guid, uri, &callbacks, 0, 0);
    if (!c)
      return 1;
    if (SetupExperiment(c, 0, 0.0, 0.0, 1, 1.0) || EnterInitializationMode(c) || ExitInitializationMode(c))
      return 1;
    for (i = 0; i < 100; ++i, t += dt) {
      if (DoStep(c, t, dt, 1))
        return 1;
    }
    if (GetReal(c, &vr, 1, &x))
      return 1;
    Terminate(c);
    FreeInstance(c);
  }

  printf("x(1) = %f, exp(-1) = %f\n", x, exp(-1.0));
  free(description);
  /* The FMU steps with explicit Euler by default: (1 - dt)^100 = 0.366. */
  return fabs(x - exp(-1.0)) < 1e-2 ? 0 : 1;
}
