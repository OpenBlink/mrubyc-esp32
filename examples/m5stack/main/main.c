#include <stdlib.h>

#include "mrubyc.h"
#include "display.h"
#include "hello_display_bytecode.h"

enum { MAX_DISPLAY_BYTES = 128 };
static _Alignas(8) uint8_t pool[32 * 1024];

static void c_display_write(mrbc_vm *vm, mrbc_value *v, int argc)
{
  if (argc != 1) {
    mrbc_raise(vm, MRBC_CLASS(ArgumentError), "display_write expects one argument");
    return;
  }
  if (mrbc_type(v[1]) != MRBC_TT_STRING) {
    mrbc_raise(vm, MRBC_CLASS(TypeError), "display_write expects a String");
    return;
  }
  int size = mrbc_string_size(&v[1]);
  if (size < 0 || size > MAX_DISPLAY_BYTES) {
    mrbc_raise(vm, MRBC_CLASS(ArgumentError), "display_write accepts at most 128 bytes");
    return;
  }
  size_t written = size == 0 ? 0 : display_write(mrbc_string_cstr(&v[1]), (size_t)size);
  SET_INT_RETURN(written);
}

void app_main(void)
{
  display_init();
  mrbc_init(pool, sizeof(pool));
  mrbc_define_method(NULL, mrbc_class_object, "display_write", c_display_write);
  if (!mrbc_create_task(hello_display_bytecode, NULL)) abort();
  if (mrbc_run() != 0) abort();
}
