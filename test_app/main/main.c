#include <stdlib.h>

#include "sdkconfig.h"
#include "mrubyc.h"
#include "hello_bytecode.h"

_Static_assert(MAX_VM_COUNT == CONFIG_MRUBYC_MAX_VM_COUNT, "VM count mismatch");
_Static_assert(MAX_REGS_SIZE == CONFIG_MRUBYC_MAX_REGS_SIZE, "register count mismatch");
_Static_assert(MAX_SYMBOLS_COUNT == CONFIG_MRUBYC_MAX_SYMBOLS_COUNT, "symbol count mismatch");
_Static_assert(MRBC_USE_FLOAT == CONFIG_MRUBYC_FLOAT_VALUE, "float mode mismatch");
_Static_assert(MRBC_TICK_UNIT == CONFIG_MRUBYC_TICK_VALUE, "tick period mismatch");
_Static_assert(MRBC_TIMESLICE_TICK_COUNT == CONFIG_MRUBYC_TIMESLICE_TICK_COUNT, "time slice mismatch");
#if defined(CONFIG_MRUBYC_USE_MATH) != MRBC_USE_MATH
#error "Math mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_USE_STRING_UTF8) != MRBC_USE_STRING_UTF8
#error "UTF-8 mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_USE_UNICODE_CASE) != MRBC_USE_UNICODE_CASE
#error "Unicode casing mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_SCHEDULER_EXIT) != MRBC_SCHEDULER_EXIT
#error "Scheduler exit mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_DEBUG) != defined(MRBC_DEBUG)
#error "Debug layout mismatch"
#endif
#if defined(CONFIG_MRUBYC_INT64) != defined(MRBC_INT64)
#error "Integer width mismatch"
#endif
#if defined(CONFIG_MRUBYC_SUPPORT_OP_EXT) != defined(MRBC_SUPPORT_OP_EXT)
#error "Extended opcode mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_ALLOC_LIBC) != defined(MRBC_ALLOC_LIBC)
#error "Allocator mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_NO_TIMER) != defined(MRBC_NO_TIMER)
#error "Timer mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_CONVERT_CRLF) != defined(MRBC_CONVERT_CRLF)
#error "Console mode mismatch"
#endif

static _Alignas(8) uint8_t pool[32 * 1024];

void app_main(void)
{
  mrbc_init(pool, sizeof(pool));
  if (!mrbc_create_task(hello_bytecode, NULL)) abort();
  if (mrbc_run() != 0) abort();
}
