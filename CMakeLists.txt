set(mrubyc_dir "${CMAKE_CURRENT_LIST_DIR}/vendor/mrubyc")

idf_component_register(
    SRC_DIRS "${mrubyc_dir}/src" "${mrubyc_dir}/hal/esp32"
    INCLUDE_DIRS "${mrubyc_dir}/src" "${mrubyc_dir}/hal/esp32"
    REQUIRES freertos
    PRIV_REQUIRES esp_driver_gptimer soc
)

if(CONFIG_GPTIMER_ISR_CACHE_SAFE AND NOT CONFIG_MRUBYC_NO_TIMER)
    message(FATAL_ERROR
        "mruby/c GPTimer callback is not cache-safe. "
        "Disable CONFIG_GPTIMER_ISR_CACHE_SAFE or enable CONFIG_MRUBYC_NO_TIMER.")
endif()

target_compile_definitions(${COMPONENT_LIB} PUBLIC
    MAX_VM_COUNT=${CONFIG_MRUBYC_MAX_VM_COUNT}
    MAX_REGS_SIZE=${CONFIG_MRUBYC_MAX_REGS_SIZE}
    MAX_SYMBOLS_COUNT=${CONFIG_MRUBYC_MAX_SYMBOLS_COUNT}
    MRBC_USE_FLOAT=${CONFIG_MRUBYC_FLOAT_VALUE}
    MRBC_USE_MATH=$<BOOL:${CONFIG_MRUBYC_USE_MATH}>
    MRBC_USE_STRING_UTF8=$<BOOL:${CONFIG_MRUBYC_USE_STRING_UTF8}>
    MRBC_USE_UNICODE_CASE=$<BOOL:${CONFIG_MRUBYC_USE_UNICODE_CASE}>
    MRBC_SCHEDULER_EXIT=$<BOOL:${CONFIG_MRUBYC_SCHEDULER_EXIT}>
    MRBC_TIMESLICE_TICK_COUNT=${CONFIG_MRUBYC_TIMESLICE_TICK_COUNT}
    MRBC_TICK_UNIT=${CONFIG_MRUBYC_TICK_VALUE}
)

foreach(option IN ITEMS INT64 SUPPORT_OP_EXT ALLOC_LIBC NO_TIMER CONVERT_CRLF)
    if(CONFIG_MRUBYC_${option})
        target_compile_definitions(${COMPONENT_LIB} PUBLIC MRBC_${option}=1)
    endif()
endforeach()

if(NOT CONFIG_MRUBYC_DEBUG)
    target_compile_definitions(${COMPONENT_LIB} PUBLIC NDEBUG)
endif()

target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-error=implicit-fallthrough)
include(CheckCCompilerFlag)
check_c_compiler_flag("-Wunterminated-string-initialization" MRUBYC_HAS_UNTERMINATED_STRING_WARNING)
if(MRUBYC_HAS_UNTERMINATED_STRING_WARNING)
    target_compile_options(${COMPONENT_LIB} PRIVATE -Wno-error=unterminated-string-initialization)
endif()
