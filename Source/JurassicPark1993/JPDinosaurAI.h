#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "JPDinosaurAI.generated.h"

UENUM(BlueprintType)
enum class EJPAnimalState : uint8
{
    Idle,
    Roam,
    Alert,
    Investigate,
    Chase,
    Attack,
    Flee
};

UCLASS()
class JURASSICPARK1993_API AJPDinosaurAI : public ACharacter
{
    GENERATED_BODY()

public:
    AJPDinosaurAI();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AI")
    EJPAnimalState State = EJPAnimalState::Idle;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AI")
    float SightRadius = 2500.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="AI")
    float AttackDistance = 180.0f;

    UFUNCTION(BlueprintCallable, Category="AI")
    void SetAnimalState(EJPAnimalState NewState);
};
