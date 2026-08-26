#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JPMissionTrigger.generated.h"

class UBoxComponent;

UCLASS()
class JURASSICPARK1993_API AJPMissionTrigger : public AActor
{
    GENERATED_BODY()

public:
    AJPMissionTrigger();

protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly)
    UBoxComponent* Trigger;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mission")
    FName ObjectiveId;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mission")
    FString ObjectiveText;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mission")
    bool bCompleteExistingObjective = false;

    UFUNCTION()
    void OnTriggerEntered(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
        UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep,
        const FHitResult& SweepResult);
};
