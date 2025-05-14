# Design Documents - Historical Reference

## Important Notice

**The design documents in this directory represent design proposals created during the CREATIVE phase and do not accurately reflect the final implementation.**

For an accurate description of how the actual implementation compares to these design proposals, please refer to the `implementation-reality.md` document in this directory.

## Design Proposal Files

This directory contains the following design proposal documents:

1. **tiered-loyalty-algorithm.md** - Proposed design for the loyalty algorithm with tiered structure
2. **blockchain-event-processing.md** - Proposed approach for fetching and processing blockchain events
3. **state-management-system.md** - Proposed design for state persistence and management
4. **data-model-design.md** - Proposed data structures and relationships

## Actual Implementation

The actual implementation took a more pragmatic approach than what was outlined in these design documents. The code is focused on reliable functionality rather than implementing the full architectural complexity described in these documents.

Key aspects of the actual implementation:

- Simple JSON file-based storage instead of SQLite
- Straightforward event processing without complex parallelism
- Simplified time-weighted calculation without explicit tier multipliers
- Basic data structures optimized for the specific use case

## Why Keep These Documents?

These documents are retained for:

1. **Historical reference** - They document the design thinking process
2. **Future enhancements** - They contain ideas that might be implemented in future versions
3. **Knowledge preservation** - They capture detailed analysis that may be valuable

## Next Steps

If maintaining accurate documentation is a priority, consider either:

1. Updating these design documents to reflect the actual implementation
2. Clearly marking them as "historical design proposals" and creating new documentation for the actual implementation

The `implementation-reality.md` file serves as a bridge between these design proposals and the actual implementation. 