#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "JPObjectiveComponent.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOnObjectiveChanged, FName, ObjectiveId, FString, ObjectiveText);

UCLASS(ClassGroup=(JP), meta=(BlueprintSpawnableComponent))
class JURASSICPARK1993_API UJPObjectiveComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UJPObjectiveComponent();

    UPROPERTY(BlueprintAssignable, Category="Objectives")
    FOnObjectiveChanged OnObjectiveChanged;

    UFUNCTION(BlueprintCallable, Category="Objectives")
    void SetObjective(FName ObjectiveId, const FString& ObjectiveText);

    UFUNCTION(BlueprintCallable, Category="Objectives")
    void CompleteObjective();

    UFUNCTION(BlueprintPure, Category="Objectives")
    FName GetCurrentObjectiveId() const { return CurrentObjectiveId; }

    UFUNCTION(BlueprintPure, Category="Objectives")
    FString GetCurrentObjectiveText() const { return CurrentObjectiveText; }

private:
    UPROPERTY()
    FName CurrentObjectiveId;

    UPROPERTY()
    FString CurrentObjectiveText;
};
