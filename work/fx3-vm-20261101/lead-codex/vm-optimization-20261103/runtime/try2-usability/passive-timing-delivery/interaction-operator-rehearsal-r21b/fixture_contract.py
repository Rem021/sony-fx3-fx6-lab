"""Controlled historical PNG completion; mirrors original runner final-review gate."""
def complete_review(state):
 state.require_visual_review(1,'visual_changed',True)
 snapshot=state.snapshot()
 if not (snapshot['review_required'] and snapshot['review_step']==1 and snapshot['visual_state']=='visual_changed' and snapshot['input_received'] and snapshot['visual_change_observed'] and not snapshot['busy']):
  raise AssertionError('invalid complete fixture review state')
 return snapshot
