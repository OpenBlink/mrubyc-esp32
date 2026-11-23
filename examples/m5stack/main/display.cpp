#include <M5Unified.h>

#include "display.h"

void display_init(void)
{
  M5.begin(M5.config());
}

size_t display_write(const char *text, size_t size)
{
  return M5.Display.write(text, size);
}
