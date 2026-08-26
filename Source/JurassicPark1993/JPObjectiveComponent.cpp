#include "JPObjectiveComponent.h"

UJPObjectiveComponent::UJPObjectiveComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UJPObjectiveComponent::SetObjective(FName ObjectiveId, const FString& ObjectiveText)
{
    CurrentObjectiveId = ObjectiveId;
    CurrentObjectiveText = ObjectiveText;
    OnObjectiveChanged.Broadcast(CurrentObjectiveId, CurrentObjectiveText);
}

void UJPObjectiveComponent::CompleteObjective()
{
    CurrentObjectiveId = NAME_None;
    CurrentObjectiveText.Empty();
    OnObjectiveChanged.Broadcast(CurrentObjectiveId, CurrentObjectiveText);
}
