#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sdkconfig.h"
#include "mrubyc.h"
#include "hello_bytecode.h"

_Static_assert(MRBC_EXCEPTION_CALL_NEST_LEVEL == CONFIG_MRUBYC_EXCEPTION_CALL_NEST_LEVEL,
               "exception backtrace capacity mismatch");
_Static_assert(sizeof(((mrbc_exception *)0)->call_nest) / sizeof(mrbc_sym) ==
               CONFIG_MRUBYC_EXCEPTION_CALL_NEST_LEVEL, "exception layout mismatch");
_Static_assert(sizeof(((mrbc_tcb *)0)->name) == CONFIG_MRUBYC_TASK_NAME_LEN + 1,
               "task name layout mismatch");
#if defined(CONFIG_MRUBYC_ALLOC_PROFILING) != defined(MRBC_USE_ALLOC_PROF)
#error "Allocator profiling mode mismatch"
#endif
#if defined(CONFIG_MRUBYC_DISABLE_LEGACY_VALUE_MACROS) == defined(GET_TT_ARG)
#error "Legacy value macro mode mismatch"
#endif
#if defined(MRBC_OUT_OF_MEMORY) || defined(MRBC_ABORT_BY_EXCEPTION)
#error "Private fatal hooks leaked to consumer"
#endif
#if defined(CONFIG_MRUBYC_ALLOC_LIBC) && (defined(CONFIG_MRUBYC_OOM_POOL_STATS) || defined(CONFIG_MRUBYC_ALLOC_PROFILING))
#error "Pool-only options enabled under libc allocation"
#endif

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

#if defined(CONFIG_MRUBYC_TEST_PARITY)
#include "parity_bytecode.h"
#endif
#if defined(CONFIG_MRUBYC_TEST_PARITY) || defined(CONFIG_MRUBYC_TEST_EXCEPTION)
#include "unhandled_bytecode.h"
#endif

#ifdef CONFIG_MRUBYC_TEST_PARITY
static void check_runtime_options(void)
{
  struct MRBC_ALLOC_PROF profile;
  mrbc_alloc_start_profiling();
  void *allocation = mrbc_raw_alloc(512);
  mrbc_raw_free(allocation);
  mrbc_alloc_stop_profiling();
  mrbc_alloc_get_profiling(&profile);
  if (profile.max < profile.initial + 512 || profile.min != profile.initial) abort();

  static char keys[CONFIG_MRUBYC_KV_SIZE_INIT + 1][24];
  mrbc_kv_handle table;
  mrbc_kv_init_handle(NULL, &table, 0);
  for (int i = 0; i <= CONFIG_MRUBYC_KV_SIZE_INIT; ++i) {
    snprintf(keys[i], sizeof(keys[i]), "parity_key_%d", i);
    mrbc_sym id = mrbc_str_to_symid(keys[i]);
    if (id < 0) abort();
    mrbc_value value = mrbc_integer_value(i);
    if (mrbc_kv_set(&table, id, &value) != 0) abort();
    if (mrbc_integer(*mrbc_kv_get(&table, id)) != i) abort();
    if (i == 0 && table.data_size != CONFIG_MRUBYC_KV_SIZE_INIT) abort();
  }
  if (table.data_size != CONFIG_MRUBYC_KV_SIZE_INIT + CONFIG_MRUBYC_KV_SIZE_INCREMENT) abort();
  for (int i = 0; i <= CONFIG_MRUBYC_KV_SIZE_INIT; ++i) {
    mrbc_value *value = mrbc_kv_get(&table, mrbc_str_to_symid(keys[i]));
    if (!value || mrbc_integer(*value) != i) abort();
  }
  mrbc_kv_delete_data(&table);

  mrbc_tcb *task = mrbc_create_task(parity_bytecode, NULL);
  if (!task) abort();
  char name[CONFIG_MRUBYC_TASK_NAME_LEN + 2];
  memset(name, 'x', sizeof(name) - 1);
  name[sizeof(name) - 1] = '\0';
  mrbc_set_task_name(task, name);
  if (strlen(task->name) != CONFIG_MRUBYC_TASK_NAME_LEN) abort();
  if (mrbc_run() != 0) abort();
  puts("Runtime options verified");

  task = mrbc_tcb_new(MAX_REGS_SIZE, MRBC_TASK_DEFAULT_STATE, MRBC_TASK_DEFAULT_PRIORITY);
  task->vm.flag_permanence = 1;
  if (!mrbc_create_task(unhandled_bytecode, task) || mrbc_run() == 0) abort();
  puts("Permanent task bypassed the teardown hook");
}
#endif

void app_main(void)
{
  mrbc_init(pool, sizeof(pool));
#if defined(CONFIG_MRUBYC_TEST_PARITY)
  check_runtime_options();
#elif defined(CONFIG_MRUBYC_TEST_OOM)
  puts("Triggering pool exhaustion");
  (void)mrbc_raw_alloc(sizeof(pool));
  puts("Pool exhaustion returned unexpectedly");
#elif defined(CONFIG_MRUBYC_TEST_EXCEPTION)
  puts("Triggering unhandled exception");
  if (!mrbc_create_task(unhandled_bytecode, NULL) || mrbc_run() == 0) abort();
  puts("Scheduler returned the exception status");
#else
  if (!mrbc_create_task(hello_bytecode, NULL)) abort();
  if (mrbc_run() != 0) abort();
#endif
}
