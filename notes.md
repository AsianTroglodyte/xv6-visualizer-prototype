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

## Overall Conclusion

`QEMU` is enough for most of the important OS concepts across CPU virtualization, memory virtualization, persistence, and concurrency.

`xv6` is a good substrate for making those concepts visible, but it will need targeted instrumentation and some kernel hacking to produce clean visualizations.

The hardest unit is security. It is still adaptable, but it is less naturally visual than the others and will require more custom design to keep it simple for students.

If the project stays focused on small, concrete demos, the combination of `xv6` plus `QEMU` should be sufficient for the majority of the OSTEP material we care about.

## Instrumentation Note

If we add xv6 hooks for visualization, the cleanest approach is to keep them generic and tightly co-located.

- emit semantic events from the kernel
- keep rendering logic outside xv6
- prefer one-line hook calls or small helper macros
- use preprocessor switches only to enable or disable tracing, not to encode visualization behavior

That keeps the kernel clean while still letting an external tool observe process, memory, filesystem, and synchronization state.

## Concurrency Prototype

For the first concurrency proof of concept, the project uses a synthetic contended lock rather than tracing every lock in xv6.

- one dedicated kernel lock is enough to show contention clearly
- the visualizer can split each acquisition into waiting time and critical-section time
- this keeps the xv6 changes isolated and avoids polluting the rest of the kernel with demo-specific code
