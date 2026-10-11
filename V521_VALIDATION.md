# v5.21 validation

The clip editor now checks the loaded posting module's API before importing its controls. A server retaining the previous two-argument post_form is refreshed from the updated local file. Current controls are reused without a reload on ordinary editor reruns. No server restart or session reset is required.

A regression test first reproduced the reported TypeError at the app's three-argument call. After the repair it opened the Social media controls, retained the saved manual title and posting file, and reused the existing export. Another test verifies that current posting controls are not unnecessarily reloaded.

227 tests passed in 13.840 seconds, including the two new regression checks. Python compilation and git diff checks passed.

The already-running local server was rerun through its visible Rerun button and displayed v5.21. Opening the latest saved project, reviewing its first clip and selecting Social media displayed the selected local AI writer, both generation buttons and editable posting fields without the reported error. No text was generated, saved or published during this browser check. The preview rendered one new clip through the normal editor workflow.

All 1,340 inventoried pre-existing files other than that project's finished-clips registry retained their sizes and modification times. The registry was updated by the normal preview registration. The check created a final package, render manifest and one MP4 with its caption/framing/timeline sidecars; no existing source video, transcript, export or model file was replaced. Inventories, regression output and a screenshot are under work/v521-validation/, excluded from Git.

The user-visible version is v5.21. Analysis-cache versions are unchanged. The repair specifically handles the older posting-form API; it is not a general live reload system for every module.
