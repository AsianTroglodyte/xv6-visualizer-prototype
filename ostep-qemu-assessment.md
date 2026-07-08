# OSTEP x QEMU x xv6 Assessment

This is a chapter-level pass over the main OSTEP units, based on the official OSTEP table of contents and chapter PDFs, plus QEMU's documented system and block options.

Sources:

- [OSTEP home and TOC](https://pages.cs.wisc.edu/~remzi/OSTEP/)
- [QEMU Invocation](https://www.qemu.org/docs/master/system/invocation.html)
- [QEMU block drivers](https://www.qemu.org/docs/master/system/qemu-block-drivers.html)

## High-Level Verdict

| Unit | QEMU fit | xv6 fit | Extra xv6 hacking | Student clarity |
| --- | --- | --- | --- | --- |
| CPU virtualization | High | High | Moderate | High |
| Memory virtualization | High | High | Moderate | High |
| Persistence | High for filesystem behavior, low for true disk internals | High | Moderate to high | Medium to high |
| Concurrency | High | High | Moderate | High |
| Security | Medium | Medium | High | Medium |

## What QEMU Gives Us

QEMU is strong at the guest-machine boundary:

- CPU models and multiple vCPUs
- machine selection
- memory sizing and NUMA layout
- deterministic/debug-friendly execution options like `-icount`, logging, and record/replay
- block backends and device models like `virtio-blk`, `virtio-scsi`, `nvme`, IDE, SCSI, SD, and raw/qcow2 storage
- storage behavior knobs such as cache mode, `aio`, flush behavior, discard, write-cache, and throttling

QEMU is weak at the microarchitectural or device-internal layer unless we instrument it ourselves:

- real cache hierarchy behavior
- true page-walk or TLB internals as a visualization target
- NAND/SSD firmware behavior
- wear leveling
- device-internal buffering and controller-specific heuristics

## Illustration Strategy

The most useful OSTEP figures are not the chapter keywords themselves but the recurring visual patterns:

- process-state timelines and scheduler Gantt charts
- arrows across the user/kernel boundary
- address-space rectangles and page-table walk diagrams
- translation-cache overlays and fault paths
- disk layout sketches, block maps, and write-order diagrams
- lock and condition-variable wait queues
- permission matrices and trust-boundary diagrams

If a concept cannot be expressed in one of those forms, it will usually be harder to teach cleanly.

## 1. CPU Virtualization

Official OSTEP chapters in this unit:

- `Processes`
- `Process API`
- `Direct Execution`
- `CPU Scheduling`
- `Multi-level Feedback`
- `Lottery Scheduling`
- `Multi-CPU Scheduling`
- `Summary`

### Processes

Core concepts:

- a process is a running program
- process state includes registers, PC, stack, heap, open files
- time sharing creates the illusion of many CPUs

Best illustration:

- a process-state diagram
- a timeline showing `running`, `ready`, and `blocked`
- arrows for `fork`, `sleep`, `wakeup`, and `exit`

QEMU fit:

- strong
- QEMU can run xv6 and expose the real process abstraction from the guest side

xv6 fit:

- strong

What xv6 hacking would help:

- scheduler tracing
- process state timeline visualization
- explicit load/run/block/exit instrumentation

Student clarity:

- high
- this is one of the easiest concepts to present visually

### Process API

Core concepts:

- create
- destroy
- wait
- suspend/resume
- status

Best illustration:

- a lifecycle diagram from creation to exit
- a call/return sequence for `fork`, `exec`, `wait`, and `kill`

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- visible events for process creation and teardown

Student clarity:

- high

### Direct Execution

Core concepts:

- run code directly on hardware for speed
- trap into the kernel for privileged operations
- use the trap path for protection and control
- timer interrupts enable preemption

Best illustration:

- a user/kernel boundary diagram
- trap and return arrows
- timer interrupt preemption on a timeline

QEMU fit:

- strong
- `-icount` and logging can help make execution transitions visible

xv6 fit:

- strong

What xv6 hacking would help:

- expose trap causes and return paths
- show when control switches user -> kernel -> user

Student clarity:

- high

### CPU Scheduling

Core concepts:

- job length and latency vs throughput tradeoffs
- FIFO, SJF, RR, priority ideas
- fairness and responsiveness

Best illustration:

- a Gantt chart of CPU use
- response-time vs turnaround-time comparison
- policy comparison across the same workload

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- scheduler traces
- wait-time and runtime accounting
- side-by-side comparison of policies

Student clarity:

- high

### Multi-Level Feedback Queue

Core concepts:

- dynamic priorities
- promotion and demotion
- interactive vs CPU-bound behavior

Best illustration:

- stacked queues by priority
- arrows for promotion and demotion
- CPU-bound vs interactive process movement

QEMU fit:

- strong

xv6 fit:

- strong, but requires scheduler changes

What xv6 hacking would help:

- policy implementation in xv6's scheduler
- per-process priority state
- visual queue transitions

Student clarity:

- high if the queue movement is shown explicitly

### Lottery Scheduling

Core concepts:

- probabilistic fairness
- tickets as resource shares
- stochastic scheduling outcomes

Best illustration:

- ticket pools
- a lottery draw wheel or selection line
- repeated draws showing approximate fairness over time

QEMU fit:

- strong

xv6 fit:

- strong, but requires scheduler replacement or augmentation

What xv6 hacking would help:

- ticket accounting
- random draw visualization
- repeated-run comparison to show approximate fairness

Student clarity:

- medium to high

### Multi-CPU Scheduling

Core concepts:

- load balancing
- per-CPU run queues
- cache affinity
- locking in the scheduler

Best illustration:

- one run queue per CPU
- migration arrows between CPUs
- lock contention markers around scheduler data

QEMU fit:

- strong
- QEMU can expose multiple vCPUs

xv6 fit:

- strong, but it is the most involved scheduler work in the CPU unit

What xv6 hacking would help:

- SMP scheduler instrumentation
- per-CPU queue visualization
- lock-contention tracing

Student clarity:

- high if kept to a few CPUs and a small number of processes

### CPU Summary

This unit is one of the best fits for xv6 + QEMU.

Why it works:

- the key ideas are visible from the guest side
- the implementation details are small enough to instrument
- the visuals map cleanly to timelines and state diagrams

## 2. Memory Virtualization

Official OSTEP chapters in this unit:

- `Address Spaces`
- `Memory API`
- `Address Translation`
- `Segmentation`
- `Introduction to Paging`
- `Translation Lookaside Buffers`
- `Advanced Page Tables`
- `Swapping: Mechanisms`
- `Swapping: Policies`
- `Complete VM Systems`
- `Summary`

### Address Spaces

Core concepts:

- a process has its own virtual address space
- code, data, heap, and stack are separate regions
- translation provides isolation and protection

Best illustration:

- a per-process memory map
- side-by-side virtual vs physical memory views

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- visual address-space maps per process
- region highlighting for text/data/heap/stack

Student clarity:

- high

### Memory API

Core concepts:

- allocation and deallocation
- `malloc`-style behavior
- heap growth intuition

Best illustration:

- heap growth bars
- allocation and free transitions

QEMU fit:

- strong

xv6 fit:

- strong enough for a simplified allocator story

What xv6 hacking would help:

- allocator tracing
- free-list or frame-use tracking

Student clarity:

- high

### Address Translation

Core concepts:

- virtual address to physical address mapping
- protection bits
- isolation

Best illustration:

- a translation pipeline: virtual address -> PTE -> physical address
- a protection-bit callout

QEMU fit:

- strong at the abstraction level

xv6 fit:

- strong

What xv6 hacking would help:

- show virtual address, PTE, and physical frame on each access
- page-fault explanations

Student clarity:

- high

### Segmentation

Core concepts:

- base and bounds
- per-segment protection
- historical alternative to paging

Best illustration:

- base/bounds bars for each segment
- translated address highlighting

QEMU fit:

- partial
- QEMU will run a guest that uses it only if the architecture and OS do

xv6 fit:

- weak for modern xv6 as-is

What xv6 hacking would help:

- a teaching mode that emulates segment-like regions conceptually

Student clarity:

- medium

### Introduction to Paging

Core concepts:

- page-sized chunks
- page tables
- page faults
- demand allocation

Best illustration:

- page-sized boxes
- page-table entries pointing to frames
- page-fault arrows into the kernel

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- page fault tracing
- page table dumps rendered as diagrams
- physical frame allocation visualization

Student clarity:

- high

### Translation Lookaside Buffers

Core concepts:

- translation caching
- hits and misses
- translation overhead

Best illustration:

- a small translation cache in front of the page-table walk
- hit/miss highlighting

QEMU fit:

- partial

xv6 fit:

- partial

What xv6 hacking would help:

- software-visible counters or traces that approximate translation behavior

Student clarity:

- medium

### Advanced Page Tables

Core concepts:

- multi-level page tables
- space/time tradeoffs
- sparse address spaces

Best illustration:

- a multi-level tree of page tables
- sparse regions with missing branches

QEMU fit:

- strong

xv6 fit:

- strong enough for a teaching implementation

What xv6 hacking would help:

- page-table walk visualization
- hierarchy display

Student clarity:

- medium to high

### Swapping: Mechanisms

Core concepts:

- move pages to disk
- page replacement
- reclaim memory under pressure

Best illustration:

- memory pressure causing eviction
- pages moving between RAM and disk

QEMU fit:

- strong for guest-visible behavior

xv6 fit:

- partial to strong, depending on how much swapping we add

What xv6 hacking would help:

- explicit swap-in/swap-out tracing
- page eviction visualization

Student clarity:

- medium

### Swapping: Policies

Core concepts:

- FIFO/LRU-like policy tradeoffs
- thrashing
- locality

Best illustration:

- working-set or reuse-distance style views
- victim selection over time

QEMU fit:

- strong

xv6 fit:

- strong enough if we add policy logic in the VM layer

What xv6 hacking would help:

- eviction policy instrumentation
- working-set demos

Student clarity:

- medium to high

### Complete VM Systems

Core concepts:

- integrating the VM pieces
- tradeoffs in a real system

Best illustration:

- a layered diagram showing translation, faults, replacement, and backing store

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- whole-system memory dashboard

Student clarity:

- medium

### Memory Summary

This unit is a very good fit.

Why it works:

- QEMU is enough for the OS concepts
- xv6 can make the state legible
- the hard part is exposing translation cleanly rather than simulating hardware detail

## 3. Persistence

Official OSTEP chapters in this unit:

- `I/O Devices`
- `Hard Disk Drives`
- `Redundant Disk Arrays (RAID)`
- `Files and Directories`
- `Free Space Management`
- `File System Implementation`
- `Fast File System (FFS)`
- `FSCK and Journaling`
- `Log-structured File System (LFS)`
- `Flash-based SSDs`
- `Data Integrity and Protection`
- `Summary`

### I/O Devices

Core concepts:

- device interfaces
- interrupts
- DMA-like behavior
- device/software separation

Best illustration:

- device request and interrupt arrows
- software versus hardware boundary

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- I/O path tracing

Student clarity:

- medium to high

### Hard Disk Drives

Core concepts:

- seek, rotation, transfer
- positioning costs
- performance differences from memory

Best illustration:

- a platter/arm geometry diagram
- a latency breakdown sketch

QEMU fit:

- partial
- QEMU can present a block device but not realistic spindle physics by default

xv6 fit:

- strong for block-level behavior

What xv6 hacking would help:

- block-access visualization
- artificial latency injection if we want the HDD mental model

Student clarity:

- high if kept conceptual

### RAID

Core concepts:

- redundancy
- striping
- fault tolerance
- performance tradeoffs

Best illustration:

- multiple-disk striping/mirroring diagrams
- failure and reconstruction arrows

QEMU fit:

- partial to strong

xv6 fit:

- partial

What xv6 hacking would help:

- mirrored or striped block abstraction
- failure injection

Student clarity:

- medium

### Files and Directories

Core concepts:

- inode-like metadata
- directory hierarchy
- naming
- linking

Best illustration:

- a directory tree
- file-to-inode-to-block pointers

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- file-tree visualization
- metadata display

Student clarity:

- high

### Free Space Management

Core concepts:

- block allocation
- bitmap / free-list tradeoffs
- fragmentation

Best illustration:

- a free-space bitmap or free-list view
- allocation and release of blocks

QEMU fit:

- strong

xv6 fit:

- strong enough for a compact filesystem

What xv6 hacking would help:

- live block bitmap visualization
- allocation traces

Student clarity:

- high

### File System Implementation

Core concepts:

- inode layout
- directory updates
- metadata blocks
- data blocks
- read/write path

Best illustration:

- on-disk layout blocks
- path lookup across directory entries
- file read/write touching metadata and data blocks

QEMU fit:

- strong

xv6 fit:

- very strong

What xv6 hacking would help:

- step-by-step file-operation traces
- on-disk layout diagrams

Student clarity:

- high

### Fast File System (FFS)

Core concepts:

- locality
- cylinder groups / placement
- performance-aware allocation

Best illustration:

- locality-aware placement on a block map
- comparison of clustered vs scattered allocation

QEMU fit:

- strong for the abstract idea
- weak for true disk geometry fidelity

xv6 fit:

- partial

What xv6 hacking would help:

- locality-aware allocator
- block-placement visualization

Student clarity:

- medium

### FSCK and Journaling

Core concepts:

- crash consistency
- consistency checking
- write ordering
- journaling / replay

Best illustration:

- write ordering before and after a crash
- a journal log with replay arrows
- a consistency checker reconstructing invariants

QEMU fit:

- very strong at the interface level
- ideal for crash/reboot experiments

xv6 fit:

- strong, but likely needs explicit crash-injection hooks

What xv6 hacking would help:

- journal state tracing
- kill-the-power style failure points
- replay visualization

Student clarity:

- medium to high

### Log-Structured File System (LFS)

Core concepts:

- append-only writing
- segment cleaning
- write amplification
- recovery via log structure

Best illustration:

- a growing append-only log
- segment cleaning

QEMU fit:

- strong for guest-visible behavior

xv6 fit:

- partial to strong

What xv6 hacking would help:

- append-log visualization
- segment cleaner visualization

Student clarity:

- medium

### Flash-based SSDs

Core concepts:

- erase-before-write
- wear leveling
- flash translation layer behavior
- asymmetry between reads, writes, and erases

Best illustration:

- erase blocks and pages
- write amplification over time

QEMU fit:

- partial
- QEMU can expose SSD-style devices and block semantics, but not faithful internal flash behavior

xv6 fit:

- weak for realism

What xv6 hacking would help:

- synthetic flash model or heavy instrumentation if we really want SSD-specific policies

Student clarity:

- medium

### Data Integrity and Protection

Core concepts:

- checksums
- corruption detection
- protection against silent errors
- recovery and verification

Best illustration:

- a checksum tied to a block
- corruption detection and recovery flow

QEMU fit:

- partial

xv6 fit:

- partial

What xv6 hacking would help:

- checksum visualization
- corruption injection hooks

Student clarity:

- medium

### Persistence Summary

This unit is one of the best fits after CPU and memory.

Why it works:

- QEMU is excellent for block-device and crash-consistency experiments
- xv6 can make the filesystem internals visible
- the weakest spot is genuine disk/SSD physics

## 4. Concurrency

Official OSTEP chapters in this unit:

- `Concurrency and Threads`
- `Thread API`
- `Locks`
- `Locked Data Structures`
- `Condition Variables`
- `Semaphores`
- `Concurrency Bugs`
- `Event-based Concurrency`
- `Monitors`
- `Summary`

### Concurrency and Threads

Core concepts:

- shared memory
- threads
- concurrent execution
- race conditions

Best illustration:

- a thread interleaving timeline
- a simple shared-state race example

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- thread-state timelines
- interleaving traces

Student clarity:

- high

### Thread API

Core concepts:

- thread creation
- join
- stack/register separation

Best illustration:

- thread creation and join arrows

QEMU fit:

- strong

xv6 fit:

- partial
- xv6 has processes, but thread API teaching may need a wrapper or kernel support

What xv6 hacking would help:

- a teaching thread layer

Student clarity:

- high if the model stays small

### Locks

Core concepts:

- mutual exclusion
- critical sections
- spin vs sleep behavior

Best illustration:

- a critical section with lock-held vs lock-free regions
- blocked waiters and ownership

QEMU fit:

- strong

xv6 fit:

- strong

What xv6 hacking would help:

- lock acquisition/release tracing
- contention visualization

Student clarity:

- high

### Locked Data Structures

Core concepts:

- making structures safe under concurrency
- lock granularity tradeoffs

Best illustration:

- a data structure with lock coverage regions

QEMU fit:

- strong

xv6 fit:

- strong enough if we add instrumented data structures

What xv6 hacking would help:

- show which lock protects which object

Student clarity:

- medium to high

### Condition Variables

Core concepts:

- wait
- signal
- broadcast
- sleeping until a condition becomes true

Best illustration:

- a waiting queue plus signal/broadcast arrows

QEMU fit:

- strong

xv6 fit:

- partial

What xv6 hacking would help:

- trace sleepers and wakeups
- show predicate state before and after signals

Student clarity:

- medium

### Semaphores

Core concepts:

- counting synchronization
- producer/consumer coordination

Best illustration:

- a counting token pool and blocked waiters

QEMU fit:

- strong

xv6 fit:

- partial to strong

What xv6 hacking would help:

- semaphore state visualization

Student clarity:

- medium to high

### Concurrency Bugs

Core concepts:

- races
- deadlock
- order dependence
- lost wakeups

Best illustration:

- a broken interleaving timeline
- deadlock cycle arrows

QEMU fit:

- strong
- `-icount` and repeatable execution can help reproduce bugs

xv6 fit:

- strong

What xv6 hacking would help:

- intentional bug injection
- trace capture at key interleavings

Student clarity:

- high if the examples are tiny and deterministic

### Event-based Concurrency

Core concepts:

- non-blocking I/O
- event loops
- state machines

Best illustration:

- an event-loop state machine

QEMU fit:

- strong

xv6 fit:

- partial

What xv6 hacking would help:

- event queue visualization

Student clarity:

- medium

### Monitors

Core concepts:

- locks plus condition variables
- structured synchronization

Best illustration:

- a combined lock plus condition-variable wrapper diagram

QEMU fit:

- strong

xv6 fit:

- partial to strong

What xv6 hacking would help:

- monitor-state tracing

Student clarity:

- medium to high

### Concurrency Summary

This is a very good fit for xv6 and a strong candidate for clear visuals.

Why it works:

- QEMU provides enough concurrency substrate
- xv6 needs instrumentation, but not fundamentally new hardware realism
- the visuals map cleanly to timelines and queue diagrams

## 5. Security

Official OSTEP chapters in this unit:

- `Introduction to Operating System Security`
- `Authentication`
- `Access Control`
- `Cryptography`
- `Distributed`

### Introduction to Operating System Security

Core concepts:

- the OS is the trust boundary for most software
- security goals include confidentiality, integrity, and availability
- system-wide privilege and isolation matter

Best illustration:

- trust boundaries around the kernel
- a diagram of who can affect what

QEMU fit:

- medium

xv6 fit:

- medium

What xv6 hacking would help:

- explicit trust-boundary visualization
- user/kernel and process-isolation traces

Student clarity:

- medium

### Authentication

Core concepts:

- proving identity
- credentials
- login and trust establishment

Best illustration:

- identity check flow
- credential-to-session transition

QEMU fit:

- weak to medium

xv6 fit:

- medium

What xv6 hacking would help:

- a simple login mechanism or token check
- credential flow visualization

Student clarity:

- medium

### Access Control

Core concepts:

- permissions
- authorization
- least privilege
- resource ownership

Best illustration:

- a permission matrix
- allow/deny arrows for files and processes

QEMU fit:

- weak to medium

xv6 fit:

- medium to strong if we make permissions explicit

What xv6 hacking would help:

- file ownership and access checks
- process privilege display
- allow/deny tracing

Student clarity:

- medium to high

### Cryptography

Core concepts:

- confidentiality and integrity primitives
- secure storage and communication
- hashes, signatures, encryption basics

Best illustration:

- plaintext, ciphertext, and key flow

QEMU fit:

- weak

xv6 fit:

- weak to medium

What xv6 hacking would help:

- only purpose-built demos

Student clarity:

- medium

### Distributed

Core concepts:

- trust across machine boundaries
- remote services
- partial trust and failure

Best illustration:

- remote trust boundary / message exchange diagram

QEMU fit:

- medium

xv6 fit:

- weak to medium

What xv6 hacking would help:

- networked toy services or multi-machine scenarios

Student clarity:

- medium

### Security Summary

This unit is the weakest fit overall.

Why:

- QEMU is not the main limiting factor
- the limiting factor is that security concepts are policy-heavy and harder to visualize
- xv6 can support them, but the demos need to be deliberately designed and will likely be more artificial than the other units

## Overall Recommendation

For a student-facing xv6 visualization project:

- start with `CPU virtualization`, `Memory virtualization`, `Concurrency`, and `Persistence`
- treat `Security` as a secondary unit that needs custom-designed examples
- use QEMU as the execution substrate, not as the thing we are trying to visualize
- keep the hardware model simple unless a specific concept truly depends on it

## Practical Conclusion

The combination of QEMU plus xv6 is enough for most of OSTEP's major conceptual material.

What it can support well:

- process scheduling
- address translation
- page faults
- file-system layout and crash consistency
- synchronization and race conditions

What it cannot model faithfully without extra work:

- real cache internals
- true disk/SSD physics
- deep security policy semantics

If the visualizations stay small, explicit, and instrumented, they should remain understandable to students.
