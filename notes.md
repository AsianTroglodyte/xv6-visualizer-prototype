# OS Visualization Infrastructure Notes

## Scope

This note records how well `QEMU` and `xv6` can support the main OSTEP units:

- CPU virtualization
- memory virtualization
- persistence
- concurrency
- security

The goal is not full hardware fidelity. The goal is to understand which concepts are realistically adaptable into a visual, student-friendly xv6-based environment, and where QEMU is enough versus where extra xv6 hacking would be required.

## Summary

| Unit | QEMU fit | xv6 fit | Extra xv6 hacking | Student clarity |
| --- | --- | --- | --- | --- |
| CPU virtualization | High | High | Moderate | High |
| Memory virtualization | High | High | Moderate | High |
| Persistence | High for filesystem behavior, low for real disk internals | High | Moderate to high | Medium to high |
| Concurrency | High | High | Moderate | High |
| Security | Medium | Medium | High | Medium |

## CPU Virtualization

Important concepts from the OSTEP CPU virtualization unit:

- process abstraction
- direct execution
- traps and system calls
- context switching
- scheduler behavior
- fairness and policy tradeoffs
- multiprocessor scheduling

What needs to be simulated or visualized:

- process state transitions
- CPU time slices
- syscall and interrupt boundaries
- when the scheduler runs and why
- per-process execution order
- lock contention and scheduling interaction on multiprocessor systems

QEMU capability:

- QEMU is a good match for these ideas because it runs the guest OS on a realistic CPU abstraction while keeping iteration fast.
- It supports multiple vCPUs, CPU model selection, and debug/logging features.
- It does not need to model pipeline details for these topics to be useful.

Need for xv6 hacking:

- Yes, if we want clear visualizations of process states, scheduling decisions, or context switches.
- xv6 would likely need hooks in the scheduler, trap path, and process lifecycle code.

Student-friendliness:

- High.
- These topics map naturally to diagrams and timelines.
- They are among the easiest concepts to present clearly in a classroom setting.

## Memory Virtualization

Important concepts from the OSTEP memory virtualization unit:

- virtual address spaces
- address translation
- segmentation
- paging
- page tables
- TLB behavior
- page faults
- swapping
- memory allocation and protection

What needs to be simulated or visualized:

- virtual-to-physical translation
- page-table walk structure
- page faults and their handling
- physical memory layout
- allocation and reuse of frames
- swapping or demand paging events
- protection failures

QEMU capability:

- QEMU is a strong fit for this unit because the guest OS can manage virtual memory normally while QEMU supplies the underlying machine model.
- It can run with different RAM sizes, SMP configurations, and memory-backend options.
- It can also support deterministic or trace-heavy runs through debugging and replay-style features.
- It does not expose a faithful hardware TLB or page-walk microarchitecture as a first-class visualization object unless we instrument around it.

Need for xv6 hacking:

- Yes, for meaningful visuals.
- xv6 would need instrumentation in the page-fault path, allocator, and page-table code.
- If we want page-table diagrams or memory maps that update live, that needs custom code.

Student-friendliness:

- High if we keep the visuals at the page-table and fault level.
- Lower if we try to show microarchitectural details that the guest cannot observe directly.

## Persistence

Important concepts from the OSTEP persistence unit:

- files and directories
- file-system implementation
- locality and layout
- free-space management
- crash consistency
- journaling
- log-structured file systems
- SSD behavior
- data integrity and recovery
- RAID concepts

What needs to be simulated or visualized:

- inode or metadata changes
- allocation of blocks and free space
- directory updates
- ordering of writes
- crash points and recovery behavior
- journaling replay
- block-level I/O patterns
- cache-flush and persistence boundaries

QEMU capability:

- QEMU is very good for file-system and block-interface behavior.
- It supports disk images, block-device backends, cache modes, async I/O, discard, write-cache controls, and multiple controller types such as `virtio-blk` and `nvme`.
- This is enough for most OS-level persistence concepts, especially crash consistency, file-system layout, and I/O behavior.
- QEMU is not a faithful simulator for actual disk or flash internals, so SSD wear leveling, NAND erase behavior, and vendor-specific firmware logic are not well modeled.

Need for xv6 hacking:

- Yes, for good educational visualization.
- xv6 would need file-system instrumentation for block allocation, metadata updates, journaling or recovery state, and crash-replay hooks.
- If the goal is to demonstrate crash consistency, xv6 probably needs explicit hooks to inject failures at well-chosen points.

Student-friendliness:

- Medium to high.
- File systems are teachable, but persistence becomes confusing if we expose too much raw block detail.
- The simplest presentations will focus on a small number of blocks, logs, and recovery steps.

## Concurrency

Important concepts from the OSTEP concurrency unit:

- threads
- locks and mutual exclusion
- atomicity
- condition variables
- semaphores
- deadlock
- race conditions
- order dependence
- parallel execution and synchronization

What needs to be simulated or visualized:

- thread interleavings
- critical sections
- lock acquisition and release
- wait and wakeup behavior
- deadlock cycles
- race outcomes
- shared-state updates over time

QEMU capability:

- QEMU is a good fit because concurrency is mostly an OS-level phenomenon, not a hardware-fidelity problem.
- Multiple vCPUs let the guest exercise true concurrent behavior.
- Debugging and tracing can help make interleavings visible.

Need for xv6 hacking:

- Yes, if we want the concurrency behavior to be obvious and not just implicit in code.
- xv6 would benefit from trace hooks around locks, sleepers, wakeups, and scheduler decisions.
- For certain demonstrations, we may also need deliberate bug injection or controlled scheduling points.

Student-friendliness:

- High if we keep examples small.
- Concurrency is easiest to understand when the system is intentionally tiny and the trace is short.
- xv6 is a good substrate for this because it keeps the moving parts limited.

## Security

Important concepts from the OSTEP security unit:

- authentication
- authorization and access control
- privilege separation
- isolation
- protection boundaries
- cryptography basics
- secure system design
- attack surface reduction

What needs to be simulated or visualized:

- who can access what
- how privilege changes over time
- how process and memory isolation work
- permission checks and denials
- the effect of boundaries between users, processes, and the kernel
- sometimes, simple trust relationships or threat boundaries

QEMU capability:

- QEMU is only a partial fit here.
- It can provide a realistic isolated guest environment and separate VMs, and it has features related to secure guest execution and device security.
- But most security concepts in OSTEP are policy and OS-design topics, not emulator topics.
- QEMU will not itself make authentication or access control easier to visualize unless we build those visualizations in the guest.

Need for xv6 hacking:

- Yes, significantly.
- To teach security concepts well, xv6 would need explicit instrumentation for permission checks, user/kernel transitions, file ownership, and isolation boundaries.
- If we want to visualize security, we probably need purpose-built examples rather than generic system behavior.

Student-friendliness:

- Medium.
- The basic ideas are teachable, but security is harder to visualize cleanly than scheduling or paging.
- The best approach is likely to keep the model small and focus on one security rule at a time.

## Overall Conclusion

`QEMU` is enough for most of the important OS concepts across CPU virtualization, memory virtualization, persistence, and concurrency.

`xv6` is a good substrate for making those concepts visible, but it will need targeted instrumentation and some kernel hacking to produce clean visualizations.

The hardest unit is security. It is still adaptable, but it is less naturally visual than the others and will require more custom design to keep it simple for students.

If the project stays focused on small, concrete demos, the combination of `xv6` plus `QEMU` should be sufficient for the majority of the OSTEP material we care about.


