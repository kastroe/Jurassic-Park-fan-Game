import unreal


# CLEANUP-ONLY PASS FOR IMPORTED VISITOR CENTER AND GATE
#
# Imported models are the only preserved visible landmark actors. Legacy
# generations are hidden where fallback value matters and deleted only from
# their explicit generated namespaces. Terrain, gameplay, and unrelated park
# actors are not selected.

actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

VC_MODEL_LABEL = "B16_JP_VC_Model"
GATE_MODEL_LABEL = "B17_JP_GATE_Model"
B15_PREFIX = "B15_JP_VC_"
B16_PREFIX = "B16_JP_VC_"
B17_PREFIX = "B17_JP_GATE_"

HIDE_PREFIXES = (
    # Legacy Visitor Center generations.
    "B06_JP_VisitorCenter_",
    "B07_JP_VisitorCenter_",
    "B07_JP_VC_",
    "B08_JP_VC_",
    "B09_JP_VC_",
    "B10_JP_VC_",
    "B11_JP_VC_",
    "B12_JP_VC_",
    "B13_JP_VC_",
    # Legacy gate generations, including the B10 fallback.
    "B06_JP_Gate_",
    "B08_JP_GATE_",
    "B09_JP_GATE_",
    "B10_JP_GATE_",
    # Graybox landmark actors only.
    "GB_JP_VisitorCenter_",
    "GB_JP_TourGate_",
    # Generated fallback/site layers are hidden, not destroyed.
    B15_PREFIX,
    B16_PREFIX,
    B17_PREFIX,
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
        return bool(actor.get_editor_property("bIsTemporarilyHiddenInEditor"))
    except Exception:
        raise RuntimeError("Cannot inspect editor-hidden state for %s" % actor.get_actor_label())


def save_level():
    try:
        if unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level() is True:
            return True
    except Exception:
        pass
    try:
        return unreal.EditorLevelLibrary.save_current_level() is True
    except Exception:
        return False


vc_models = [actor for actor in all_actors() if actor.get_actor_label() == VC_MODEL_LABEL]
gate_models = [actor for actor in all_actors() if actor.get_actor_label() == GATE_MODEL_LABEL]
if len(vc_models) != 1:
    raise RuntimeError("Expected exactly one %s actor; found %d" % (VC_MODEL_LABEL, len(vc_models)))
if len(gate_models) != 1:
    raise RuntimeError("Expected exactly one %s actor; found %d" % (GATE_MODEL_LABEL, len(gate_models)))

vc_model = vc_models[0]
gate_model = gate_models[0]
vc_snapshot = snapshot(vc_models)
gate_snapshot = snapshot(gate_models)
model_hidden_before = editor_hidden_state(vc_model)
gate_hidden_before = editor_hidden_state(gate_model)

hidden_actors = []
hidden_counts = {}
previous_hidden_states = []

for actor in all_actors():
    label = actor.get_actor_label()
    if label in (VC_MODEL_LABEL, GATE_MODEL_LABEL):
        continue
    matched_prefix = next((prefix for prefix in HIDE_PREFIXES if label.startswith(prefix)), None)
    if matched_prefix:
        previous_hidden_states.append((actor, editor_hidden_state(actor)))
        hidden_actors.append(actor)
        hidden_counts[matched_prefix] = hidden_counts.get(matched_prefix, 0) + 1

def restore_visibility():
    restore_errors = []
    for actor, old_hidden in previous_hidden_states:
        try:
            actor.set_is_temporarily_hidden_in_editor(old_hidden)
        except Exception as error:
            restore_errors.append(error)
    try:
        vc_model.set_is_temporarily_hidden_in_editor(model_hidden_before)
        gate_model.set_is_temporarily_hidden_in_editor(gate_hidden_before)
    except Exception as error:
        restore_errors.append(error)
    return restore_errors


try:
    # Preserve imported models and make their intended visibility explicit.
    vc_model.set_is_temporarily_hidden_in_editor(False)
    gate_model.set_is_temporarily_hidden_in_editor(False)
    for actor in hidden_actors:
        actor.set_is_temporarily_hidden_in_editor(True)

    assert_snapshot(vc_snapshot, snapshot([vc_model]), "B16 Visitor Center model")
    assert_snapshot(gate_snapshot, snapshot([gate_model]), "B17 gate model")

    if editor_hidden_state(vc_model) or editor_hidden_state(gate_model):
        raise RuntimeError("Imported landmark model is hidden after cleanup.")
    if not all(editor_hidden_state(actor) for actor in hidden_actors):
        raise RuntimeError("One or more legacy landmark actors remain visible.")
    if not save_level():
        raise RuntimeError("Cleanup completed in memory but the level could not be saved.")
except Exception:
    restore_errors = restore_visibility()
    if not save_level() or restore_errors:
        raise RuntimeError("Cleanup failed and hidden-state rollback could not be persisted.")
    raise

unreal.log(
    "JP IMPORTED LANDMARK CLEANUP COMPLETE: hidden=%s deleted=none preserved_vc=1 preserved_gate=1"
    % hidden_counts
)
