#include <fmi4c.h>
#include <miniunz.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
  /* The miniunz component: read one member of a zip archive into memory. */
  const char* description = miniunz_onefile_to_memory(TEST_FMU, "modelDescription.xml");
  int ok = description && strstr(description, "fmiVersion=\"2.0\"") != NULL;
  printf("modelDescription.xml %s\n", ok ? "read from the archive" : "missing");
  miniunz_free(description);
  if (!ok)
    return 1;

  /* fmi4c itself: loading an FMU that does not exist must fail cleanly. */
  if (fmi4c_loadFmu("does-not-exist.fmu", "test") != NULL)
    return 1;
  printf("fmi4c_loadFmu rejected a missing FMU\n");
  return 0;
}
