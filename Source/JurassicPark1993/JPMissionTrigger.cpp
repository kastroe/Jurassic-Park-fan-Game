#include "JPMissionTrigger.h"
#include "Components/BoxComponent.h"
#include "JPObjectiveComponent.h"

AJPMissionTrigger::AJPMissionTrigger()
{
    PrimaryActorTick.bCanEverTick = false;

    Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
    RootComponent = Trigger;
    Trigger->SetCollisionProfileName(TEXT("Trigger"));
    Trigger->OnComponentBeginOverlap.AddDynamic(this, &AJPMissionTrigger::OnTriggerEntered);
}

void AJPMissionTrigger::OnTriggerEntered(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
    UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep,
    const FHitResult& SweepResult)
{
    if (!OtherActor || !OtherActor->ActorHasTag(TEXT("Player"))) return;

    if (UJPObjectiveComponent* Objectives = OtherActor->FindComponentByClass<UJPObjectiveComponent>())
    {
        if (bCompleteExistingObjective) Objectives->CompleteObjective();
        if (!ObjectiveId.IsNone()) Objectives->SetObjective(ObjectiveId, ObjectiveText);
    }

    SetActorEnableCollision(false);
}
