# mruby/c for ESP-IDF

[![ESP Component Registry](https://components.espressif.com/components/openblink/mrubyc-esp32/badge.svg)](https://components.espressif.com/components/openblink/mrubyc-esp32)
[![Build](https://github.com/OpenBlink/mrubyc-esp32/actions/workflows/build.yml/badge.svg)](https://github.com/OpenBlink/mrubyc-esp32/actions/workflows/build.yml)
[![License: BSD-3-Clause](https://img.shields.io/badge/license-BSD--3--Clause-blue.svg)](LICENSE)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/OpenBlink/mrubyc-esp32)

Run compiled Ruby scripts from an ESP-IDF application. This component packages the [mruby/c](https://github.com/mrubyc/mrubyc) virtual machine and its upstream ESP32 HAL. The HAL uses GPTimer to schedule Ruby tasks and sends VM console output to standard output.

Component **3.4.1** packages mruby/c **release3.4.1** without source changes. Compile scripts with **mruby 3.4.0's `mrbc`** (RITE0300). mruby 4.0.0 generates a different bytecode format that this version rejects. A Registry suffix such as `3.4.1~1` denotes a packaging revision, not a different VM.

## Requirements

- ESP-IDF 5.5 or later. CI covers **5.5.6, 6.0.3, and 6.1.1** on **ESP32, ESP32-C3, ESP32-S3, and ESP32-C6**.
- GPTimer support. CI runs QEMU tests on ESP32 and ESP32-C3; emulator results do not guarantee hardware behavior.
- An ESP-IDF project. Arduino-only projects, an on-device source compiler, and an interactive Ruby REPL are out of scope.

## Install

From your ESP-IDF project's root:

```sh
idf.py add-dependency "openblink/mrubyc-esp32^3.4.1"
```

Or add the dependency to `main/idf_component.yml`:

```yaml
dependencies:
  openblink/mrubyc-esp32: "^3.4.1"
```

## Run a script

Build the compiler on your host from the [mruby 3.4.0 release](https://github.com/mruby/mruby/releases/tag/3.4.0) with `rake` (Ruby/Rake and a C toolchain are required). Put its `bin/mrbc` on your path and check `mrbc --version`.

Save `puts "Hello from mruby/c"` as `hello.rb` in your project root, then generate a header:

```sh
mrbc --remove-lv -Bhello_bytecode -o main/hello_bytecode.h hello.rb
```

Include it from your application's C entry point:

```c
#include <stdlib.h>

#include "mrubyc.h"
#include "hello_bytecode.h"

static _Alignas(8) uint8_t pool[32 * 1024];

void app_main(void)
{
  mrbc_init(pool, sizeof(pool));
  if (!mrbc_create_task(hello_bytecode, NULL)) abort();
  if (mrbc_run() != 0) abort();
}
```

Alternatively, compile a binary with `mrbc --remove-lv -o main/hello.mrb hello.rb`. Add `EMBED_FILES "hello.mrb"` to your main component's `idf_component_register` call, declare `extern const uint8_t hello_mrb[] asm("_binary_hello_mrb_start");`, and pass `hello_mrb` to `mrbc_create_task`.

Only load bytecode you trust. Keep both the backing bytecode and the pool alive for the scheduler's lifetime, and invoke the VM from a single application task, not concurrently from other FreeRTOS tasks.

### Application design

- **Budget pool memory and VM slots separately.** Tasks share the pool but each needs a VM slot and its own registers. Limit long-lived objects and dynamically interned symbols, and use the pool profiling option to measure a representative workload. The profiler samples the VM pool, not the ESP-IDF heap or task stacks.
- **Let other Ruby tasks run.** Use `sleep_ms` for bounded waits and avoid blocking inside native methods. A permanent Ruby task created with `Task.create` can become dormant without closing its VM. Don't use repeated task creation as a work queue or assume a completed task releases all of its resources.
- **Keep bindings small.** See the [M5Stack binding](examples/m5stack/main) for registration and argument checks. Validate argument count, types, and ranges before native work; return immediately after setting a Ruby exception. Treat Ruby arguments as borrowed and keep a reference only when the native code needs to keep them beyond the call. Transfer newly allocated Ruby return values with `SET_RETURN` and do not release them again. Pair native resource acquisition with explicit cleanup on success and failure.
- **Keep peripherals outside the VM.** Use ISR notifications or queues and handle Ruby work in the VM's application task. Document units, ownership and timeout behavior at the binding boundary; see the [mruby Microcontroller Peripheral Interface Guide](https://github.com/mruby/microcontroller-peripheral-interface-guide/tree/514497cfe184edda842f4410cd0eaee1acbdfb9c) when designing new APIs.

## Configuration

Run `idf.py menuconfig` and open **Component config → mruby/c**. Defaults match the upstream ESP32 port except that extended operands are enabled.

| Setting (`CONFIG_MRUBYC_` prefix) | Default |
| --- | --- |
| `MAX_VM_COUNT` | 5 |
| `MAX_REGS_SIZE` | 110 |
| `MAX_SYMBOLS_COUNT` | 255 |
| Floating-point choice | Double precision (`MRBC_USE_FLOAT=2`) |
| `USE_MATH` | Off |
| String length field width | 16 bits (`uint16_t`); optionally 32 bits (`uint32_t`) |
| `USE_STRING_UTF8` | Off; String is enabled, with byte indexing |
| `USE_UNICODE_CASE` | Off; requires UTF-8 indexing |
| `INT64` | Off |
| `NAN_BOXING` | Off; only available with 32-bit integers |
| `SUPPORT_OP_EXT` | On (`MRBC_SUPPORT_OP_EXT=1`) |
| `ALLOC_LIBC` | Off; use the mruby/c pool allocator |
| `ALLOC_FLI_BIT_WIDTH` | 9; pool allocator only |
| `ALLOC_SLI_BIT_WIDTH` | 3; pool allocator only |
| `ALLOC_IGNORE_LSBS` | 4; pool allocator only |
| `MIN_MEMORY_BLOCK_SIZE` | 16 bytes (upstream's `sizeof(FREE_BLOCK)` on ESP32); pool allocator only |
| `NO_TIMER` | Off; use GPTimer |
| `SCHEDULER_EXIT` | On; return when no active Ruby tasks remain |
| Tick-period choice | 10 ms |
| `TIMESLICE_TICK_COUNT` | 1 |
| `DEBUG` | On unless ESP-IDF disables assertions |
| `CONVERT_CRLF` | Off |
| `ALLOC_PROFILING` | Off; requires the mruby/c pool allocator |
| `OOM_POOL_STATS` | Off; requires the mruby/c pool allocator |
| `PANIC_ON_UNHANDLED_EXCEPTION` | Off; aborts the firmware on an unhandled exception at VM teardown |
| `SYMBOL_SEARCH_LINEAR` | Off; use the dynamic symbol tree |
| `EXCEPTION_CALL_NEST_LEVEL` | 8 backtrace entries (1–64) |
| `TASK_NAME_LEN` | 15 bytes, excluding the terminator (1–255) |
| `KV_SIZE_INIT` | 2 entries (1–64) |
| `KV_SIZE_INCREMENT` | 5 entries (1–64) |
| `NO_STDIO` | Off; enabling it removes Ruby's `p`, `print`, `puts` and `printf`, not `sprintf` or runtime diagnostics |
| `DEBUG_REGS` | Off; enabling it logs register usage at VM teardown, not peak usage |
| `DISABLE_LEGACY_VALUE_MACROS` | Off unless NaN boxing is enabled; hides legacy C value macros such as `GET_INT_ARG` |

The floating-point choice offers single and double precision. Upstream mruby/c `release3.4.1` does not compile with `MRBC_USE_FLOAT=0` because some code still accesses floating-point fields. This release leaves the upstream source unmodified and does not offer that mode. We will re-check it for v4.0.0.

The **Read-only settings in mruby/c 3.4.1** menu lists the fixed values individually. String support, the 24-bit pool format, little-endian byte order, and the 64-bit alignment requirement stay enabled. Disabling String, using 16-bit integers, or tracking allocator VM IDs fails to build with unmodified upstream sources. The 16-bit pool format, big-endian byte order, and 32-bit alignment requirement are not selectable in this ESP32 port.

Even with 32-bit String lengths, limit exception messages to 65,535 **bytes**. In mruby/c 3.4.1, longer messages passed to `Exception.new` or the C exception constructors can have their stored length truncated. If that length wraps to zero, the exception does not free the message buffer.

Allocator tuning affects the pool's overhead and allocation granularity, not the size of the buffer passed to `mrbc_init`. Set the minimum block size to a multiple of four bytes and at least `2^ALLOC_IGNORE_LSBS`.

Changing the String length width or enabling NaN boxing changes the public C representation, so rebuild the component and all its consumers together. Before enabling NaN boxing, update native bindings that use legacy value macros: `GET_TT_ARG` and the legacy numeric helpers read bits of a Float payload as a type tag. NaN boxing automatically hides these macros. Use `mrbc_type` to check the value type, then use `mrbc_integer` or `mrbc_float` to read it.

The nominal Ruby time slice is the tick period multiplied by the timeslice count. The FreeRTOS tick period must not exceed the selected mruby/c tick period; the 1, 2, and 4 ms options require a faster FreeRTOS tick. With hardware timing disabled, the scheduler uses software ticks, not a hardware timebase.

The upstream GPTimer callback is not placed in IRAM, so it cannot be used with `CONFIG_GPTIMER_ISR_CACHE_SAFE=y`. Disable that setting or enable `CONFIG_MRUBYC_NO_TIMER` to use software ticks.

The exported compile definitions keep consumer and VM structures consistent. Don't override them separately in an application's source files. Turning off mruby/c debug uses the upstream `NDEBUG` switch and also disables C assertions in components that depend on this one.

`OOM_POOL_STATS` prints total, used, and free pool bytes before the usual out-of-memory message and abort. With `PANIC_ON_UNHANDLED_EXCEPTION` disabled, mruby/c reports the exception and the scheduler may return a nonzero status. Enabling it prints the exception and calls the ESP32 HAL's abort handler instead. It does not change rescued exceptions, bytecode load failures, or permanent tasks that skip VM teardown. ESP-IDF's panic settings determine whether the firmware halts or reboots.

## Examples

```sh
idf.py create-project-from-example "openblink/mrubyc-esp32^3.4.1:hello"
cd hello
idf.py set-target esp32
idf.py build
idf.py flash monitor
```

- [hello](examples/hello) prints a greeting, waits using the scheduler, then returns.
- [vm_tasks](examples/vm_tasks) shows interleaved output from two separate mruby/c tasks.
- [m5stack](examples/m5stack) calls M5Unified 0.3.0 from Ruby using a small C/C++ binding. It targets an ESP32-S3 M5Stack device with a display, such as Cardputer. It is **build-tested only**; no hardware behavior has been verified. `display_write` takes one String of up to 128 bytes and returns the number of bytes written; an empty String returns zero.

All examples ship generated bytecode headers, so firmware builds don't need Ruby. From a checkout, regenerate them with `bash tools/generate_bytecode.sh /path/to/mruby-3.4.0/bin/mrbc`. To build against the checkout instead of the Registry, use `bash tools/build_app.sh hello esp32` in an activated ESP-IDF environment.

## ESP32 memory footprint

The baseline is a [C app](test_app/footprint) that prints the same three lines as `hello` and waits about 50 ms using FreeRTOS. It does not link mruby/c. The Ruby app uses the default component settings and a static 32 KiB pool. Both use ESP32, ESP-IDF 6.1.1, size optimization, and the same default ESP-IDF stack and logging settings.

| Linked application size (bytes) | C baseline | mruby/c `hello` | Increase |
| --- | ---: | ---: | ---: |
| Application image | 112,720 | 185,457 | 72,737 |
| Flash-mapped code and data | 65,432 | 135,976 | 70,544 |
| Static DRAM | 12,457 | 48,194 | 35,737 |
| VM pool, included in static DRAM | 0 | 32,768 | 32,768 |

The remaining 2,969 bytes of static DRAM growth include runtime and HAL state and linker layout differences.

To reproduce from a checkout, use the activated environment from `espressif/idf:v6.1.1@sha256:2b4f966c37eaedc19542b0637a5f850b2eff9478d8e858192aa0073d92c2dc91`:

```sh
out=$(mktemp -d)
defaults="$PWD/test_app/footprint/sdkconfig.defaults"
python tools/prepare_example.py hello "$out/ruby"
for variant in c ruby; do
  project="$out/ruby"
  if [ "$variant" = c ]; then project="$PWD/test_app/footprint"; fi
  idf.py -C "$project" -B "$out/build-$variant" \
    -D "SDKCONFIG=$out/build-$variant/sdkconfig" -D "SDKCONFIG_DEFAULTS=$defaults" \
    -D IDF_TARGET=esp32 -D PROJECT_VER=3.4.1 build size size-components
done
xtensa-esp-elf-nm -S "$out/build-ruby/mrubyc_hello.elf" | awk '$NF == "pool"'
```

The linked application image does not include the bootloader or partition table. Static DRAM is the `idf.py size` DRAM row (`.data` + `.bss` here), separate from IRAM and RTC memory. These measurements do not measure runtime heap or stack usage and are not size guarantees for other targets or configurations.

## Contributing and releases

Use English for issues, pull requests, and code comments. For integration reports, include the component version, ESP-IDF version, chip, and relevant configuration. See [mruby/c upstream](https://github.com/mrubyc/mrubyc) for VM documentation.

CI builds local sources with default and alternate VM options. The component demotes two diagnostics from errors to warnings only for the vendored target: the intentional byte-array debug marker initializer (when supported by the compiler) and an intentional bytecode-loader fallthrough. Neither requires changing the VM defaults.

Merge the release changes into `main` and wait for CI to pass, then run `git fetch origin`. Push an unsigned tag for `origin/main` if it still points to the resulting release commit. If `main` has advanced, tag the release commit by SHA. Do not tag the PR branch tip after a squash merge.

Prefix the manifest version with `v` and replace a revision separator (`~`) with a dot in the Git tag: `3.4.1` uses `v3.4.1`, and `3.4.1~1` uses `v3.4.1.1`. Keep the Registry version unchanged in the manifest. The GitHub `production` environment must have required reviewers, administrator bypass disabled, and only the `v*` deployment tag policy. Before the first release, configure Registry Trusted Uploaders for `OpenBlink/mrubyc-esp32` and `upload.yml` on the staging and production registries, and allow release tags through the separate GitHub `staging` environment.

The tag-triggered workflow packages the tagged commit once, publishes that archive to staging, and builds `hello` against the exact staged version. Production approval is requested only after that build succeeds. Production rechecks the approval policy and verifies the same archive's SHA-256 before attesting and publishing it. A separate job automatically publishes the GitHub Release after the production Registry upload succeeds. The workflow stops rather than changing an existing Release for that tag. Registry versions are immutable: use **Re-run failed jobs** to retry a consumer build or GitHub release without repeating a successful Registry upload. Use a new manifest revision and tag if the package itself needs to change.

### Updating bundled mruby/c

Update upstream manually in a pull request:

1. Choose an [official mruby/c release](https://github.com/mrubyc/mrubyc/releases). Update `RELEASE` and `SHA256` in `tools/import_upstream.py` with its tag and the published SHA-256 digest of the `mrubyc-<release>.tar.gz` asset (not GitHub's generated source archive).
2. Run `python3 tools/import_upstream.py import` (Python 3.12+ and curl). It verifies the archive, replaces the bundled `src/`, `hal/esp32/`, and licenses, and updates `idf_component.yml` when the upstream version changes. Review new source files, API and HAL changes, and VM configuration defaults. If the tool flags unrecognized `src/` entries, review their purpose and update the import rules before proceeding.
3. If the compiler or RITE format changes, the import command stops before making changes. From the verified archive, replace `vendor/mrubyc` with `src/`, `hal/esp32/`, `LICENSE`, and `LICENSE.unicode`, update the component version, and regenerate the example and test headers with `bash tools/generate_bytecode.sh /path/to/matching/mrbc`.
4. Run `python3 tools/import_upstream.py check` and open a PR with the pin, vendor changes, component version, and regenerated bytecode if needed. Both commands accept `--archive PATH` to verify a local copy of the official asset without downloading it again.

CI runs the same vendor check on PRs and pushes to `main`. It compares the vendored file set and contents with the pinned archive, checks the ESP-IDF source list against the upstream Makefile, and checks that the component version matches the upstream release (allowing Registry revisions such as `3.4.1~1`). It also builds the pinned compiler from `tools/build_mrbc.sh` and regenerates the example and test headers in a temporary directory for comparison. If the upstream release requires a different compiler, update the compiler commit and SHA-256 in that script when regenerating the headers.

## License

The wrapper and examples use the [BSD 3-Clause License](LICENSE). The bundled mruby/c sources retain their [upstream BSD 3-Clause notices](vendor/mrubyc/LICENSE). The generated Unicode case tables are accompanied by the [Unicode License](vendor/mrubyc/LICENSE.unicode).