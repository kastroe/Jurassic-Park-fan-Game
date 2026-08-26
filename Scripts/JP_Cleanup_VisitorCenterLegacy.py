import unreal


# VISITOR CENTER LEGACY CLEANUP
#
# Keep the imported B16 model visible while removing visual clutter around it.
# This script deliberately uses narrow Visitor Center prefixes and never uses
# the broad B10_JP_ namespace, so the main gate remains untouched.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

B16_PREFIX = "B16_JP_VC_"
B16_MODEL_LABEL = "B16_JP_VC_Model"
B15_PREFIX = "B15_JP_VC_"
B10_GATE_PREFIX = "B10_JP_GATE_"

HIDE_PREFIXES = (
    "B06_JP_VisitorCenter_",
    "B07_JP_VisitorCenter_",
    "B08_JP_VC_",
    "B09_JP_VC_",
    "B10_JP_VC_",
    "B11_JP_VC_",
    "B12_JP_VC_",
    "B13_JP_VC_",
)


def all_actors():
    return list(actor_sub.get_all_level_actors())


def by_prefix(prefix):
    return [actor for actor in all_actors() if actor.get_actor_label().startswith(prefix)]


def snapshot(actors):
    result = []
    for actor in actors:
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        result.append((
            actor.get_actor_label(),
            (location.x, location.y, location.z),
            (rotation.pitch, rotation.yaw, rotation.roll),
            (scale.x, scale.y, scale.z),
        ))
    return sorted(result)


def assert_snapshot(before, after, name):
    if len(before) != len(after):
        raise RuntimeError("%s actor count changed" % name)
    for old, new in zip(before, after):
        if old[0] != new[0]:
            raise RuntimeError("%s actor label changed" % name)
        for old_values, new_values in zip(old[1:], new[1:]):
            for old_value, new_value in zip(old_values, new_values):
                if abs(old_value - new_value) > 0.01:
                    raise RuntimeError("%s transform changed: %s" % (name, old[0]))


def editor_hidden_state(actor):
    for method_name in ("get_is_temporarily_hidden_in_editor", "is_hidden_ed"):
        method = getattr(actor, method_name, None)
        if callable(method):
            return bool(method())
    try:
        return actor.get_editor_property("bIsTemporarilyHiddenInEditor")
    except Exception:
        raise RuntimeError("Cannot verify editor visibility for %s" % actor.get_actor_label())


model_actors = [actor for actor in all_actors() if actor.get_actor_label() == B16_MODEL_LABEL]
if len(model_actors) != 1:
    raise RuntimeError("Expected exactly one %s actor; found %d" % (B16_MODEL_LABEL, len(model_actors)))
model = model_actors[0]
model_snapshot = snapshot(model_actors)
model.set_is_temporarily_hidden_in_editor(False)

gate_actors = by_prefix(B10_GATE_PREFIX)
if not gate_actors:
    raise RuntimeError("No B10_JP_GATE_ actors found; refusing cleanup.")
gate_snapshot = snapshot(gate_actors)

hidden_counts = {}
deleted_counts = {B15_PREFIX: 0, "B16_JP_VC_non_model": 0}
hidden_actors = []

for actor in all_actors():
    label = actor.get_actor_label()

    if label == B16_MODEL_LABEL or label.startswith(B10_GATE_PREFIX):
        continue

    if label.startswith(B15_PREFIX):
        actor_sub.destroy_actor(actor)
        deleted_counts[B15_PREFIX] += 1
        continue

    if label.startswith(B16_PREFIX):
        actor_sub.destroy_actor(actor)
        deleted_counts["B16_JP_VC_non_model"] += 1
        continue

    matched_prefix = next((prefix for prefix in HIDE_PREFIXES if label.startswith(prefix)), None)
    if matched_prefix:
        actor.set_is_temporarily_hidden_in_editor(True)
        hidden_actors.append(actor)
        hidden_counts[matched_prefix] = hidden_counts.get(matched_prefix, 0) + 1

assert_snapshot(model_snapshot, snapshot([model]), "B16 imported model")
assert_snapshot(gate_snapshot, snapshot(by_prefix(B10_GATE_PREFIX)), "B10 gate")

if len([actor for actor in all_actors() if actor.get_actor_label() == B16_MODEL_LABEL]) != 1:
    raise RuntimeError("Imported B16 model was not preserved.")
model_hidden = editor_hidden_state(model)
if model_hidden:
    raise RuntimeError("Imported B16 model is hidden after cleanup.")
for actor in hidden_actors:
    if not editor_hidden_state(actor):
        raise RuntimeError("Legacy Visitor Center actor remains visible: %s" % actor.get_actor_label())
if by_prefix(B15_PREFIX):
    raise RuntimeError("B15 Visitor Center helpers remain after cleanup.")
if [actor for actor in by_prefix(B16_PREFIX) if actor.get_actor_label() != B16_MODEL_LABEL]:
    raise RuntimeError("Non-model B16 Visitor Center actors remain after cleanup.")

try:
    save_result = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    if save_result is not True:
        raise RuntimeError("Primary level save did not return True.")
except Exception:
    save_result = unreal.EditorLevelLibrary.save_current_level()
    if save_result is not True:
        raise RuntimeError("Fallback level save did not return True.")

unreal.log(
    "JP VC LEGACY CLEANUP COMPLETE: hidden=%s deleted=%s preserved_model=1 protected_gate=%d"
    % (hidden_counts, deleted_counts, len(gate_actors))
)
