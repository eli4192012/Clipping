# v5.5 validation

- 114 regression tests passed, including new default-layout, legacy-label, manual-layout preservation and uncertain-action fallback tests.
- A real one-second export of the supplied portrait example, with vertical=True and no explicit layout, entered automatic framing, preserved its native composition and decoded at 720x1280 without added blur.
- Changed Python modules compile successfully. Previous v5.4 crop geometry and safety regression tests remain passing.

Automatic layout is shared by all content modes. The detector samples faces, not the ball or all objects; wide sports action or uncertain framing retains blur. Existing manual styles are preserved. No new action-tracking capability is claimed.
