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

## Configuration

Run `idf.py menuconfig` and open **Component config → mruby/c**. Defaults match the upstream ESP32 port except that extended operands are enabled.

| Setting (`CONFIG_MRUBYC_` prefix) | Default |
| --- | --- |
| `MAX_VM_COUNT` | 5 |
| `MAX_REGS_SIZE` | 110 |
| `MAX_SYMBOLS_COUNT` | 255 |
| Floating-point choice | Double precision (`MRBC_USE_FLOAT=2`) |
| `USE_MATH` | Off |
| `USE_STRING_UTF8` | Off; String is enabled, with byte indexing |
| `USE_UNICODE_CASE` | Off; requires UTF-8 indexing |
| `INT64` | Off |
| `SUPPORT_OP_EXT` | On (`MRBC_SUPPORT_OP_EXT=1`) |
| `ALLOC_LIBC` | Off; use the mruby/c pool allocator |
| `NO_TIMER` | Off; use GPTimer |
| `SCHEDULER_EXIT` | On; return when no active Ruby tasks remain |
| Tick-period choice | 10 ms |
| `TIMESLICE_TICK_COUNT` | 1 |
| `DEBUG` | On unless ESP-IDF disables assertions |
| `CONVERT_CRLF` | Off |

The floating-point choice offers single and double precision. Upstream mruby/c `release3.4.1` does not compile with `MRBC_USE_FLOAT=0` because some code still accesses floating-point fields. This release leaves the upstream source unmodified and does not offer that mode. We will re-check it for v4.0.0.

The nominal Ruby time slice is the tick period multiplied by the timeslice count. The FreeRTOS tick period must not exceed the selected mruby/c tick period; the 1, 2, and 4 ms options require a faster FreeRTOS tick. With hardware timing disabled, the scheduler uses software ticks, not a hardware timebase.

The upstream GPTimer callback is not placed in IRAM, so it cannot be used with `CONFIG_GPTIMER_ISR_CACHE_SAFE=y`. Disable that setting or enable `CONFIG_MRUBYC_NO_TIMER` to use software ticks.

The exported compile definitions keep consumer and VM structures consistent. Don't override them separately in an application's source files. Turning off mruby/c debug uses the upstream `NDEBUG` switch and also disables C assertions in components that depend on this one.

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

## Contributing and releases

Use English for issues, pull requests, and code comments. For integration reports, include the component version, ESP-IDF version, chip, and relevant configuration. See [mruby/c upstream](https://github.com/mrubyc/mrubyc) for VM documentation.

CI builds local sources with default and alternate VM options. The component demotes two diagnostics from errors to warnings only for the vendored target: the intentional byte-array debug marker initializer (when supported by the compiler) and an intentional bytecode-loader fallthrough. Neither requires changing the VM defaults.

Validate the package and a staging Registry consumer before tagging a release. Prefix the manifest version with `v` and replace a revision separator (`~`) with a dot in the Git tag: `3.4.1` uses `v3.4.1`, and `3.4.1~1` uses `v3.4.1.1`. Keep the Registry version unchanged in the manifest. Configure required reviewers and release tag restrictions on the GitHub `production` environment, and configure the Registry Trusted Uploader for `OpenBlink/mrubyc-esp32` and `upload.yml` before the first release. The manually dispatched staging job uses a separate `staging` environment and staging Registry trust configuration.

Staging publishes the archive inspected by the package job and fails if that version already exists. Use a new manifest revision for another staging upload; a rerun does not replace the previous package.

The upstream import workflow requires the repository setting that allows GitHub Actions to create pull requests. Review its PRs for API, configuration, and compiler changes; regenerate example bytecode if the compiler changes before merging.

## License

The wrapper and examples use the [BSD 3-Clause License](LICENSE). The bundled mruby/c sources retain their [upstream BSD 3-Clause notices](vendor/mrubyc/LICENSE). The generated Unicode case tables are accompanied by the [Unicode License](vendor/mrubyc/LICENSE.unicode).