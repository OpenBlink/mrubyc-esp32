#include <stdio.h>
#include <stdlib.h>

#include "mrubyc.h"
#include "hello_bytecode.h"

static _Alignas(8) uint8_t pool[32 * 1024];

void app_main(void)
{
  mrbc_init(pool, sizeof(pool));
  if (!mrbc_create_task(hello_bytecode, NULL)) abort();
  if (mrbc_run() != 0) abort();
  puts("mruby/c scheduler finished");
}
