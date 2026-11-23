#include <stdio.h>
#include <stdlib.h>

#include "mrubyc.h"
#include "first_bytecode.h"
#include "second_bytecode.h"

static _Alignas(8) uint8_t pool[48 * 1024];

void app_main(void)
{
  mrbc_init(pool, sizeof(pool));
  if (!mrbc_create_task(first_bytecode, NULL)) abort();
  if (!mrbc_create_task(second_bytecode, NULL)) abort();
  if (mrbc_run() != 0) abort();
  puts("Both mruby/c tasks finished");
}
