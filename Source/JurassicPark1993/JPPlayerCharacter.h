#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "JPPlayerCharacter.generated.h"

class UCameraComponent;
class UInputMappingContext;
class UInputAction;
class UJPObjectiveComponent;
struct FInputActionValue;

UCLASS()
class JURASSICPARK1993_API AJPPlayerCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    AJPPlayerCharacter();

protected:
    virtual void BeginPlay() override;
    virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Camera")
    UCameraComponent* FirstPersonCamera;

    UPROPERTY(EditDefaultsOnly, Category="Input")
    UInputMappingContext* DefaultMappingContext;

    UPROPERTY(EditDefaultsOnly, Category="Input")
    UInputAction* MoveAction;

    UPROPERTY(EditDefaultsOnly, Category="Input")
    UInputAction* LookAction;

    UPROPERTY(EditDefaultsOnly, Category="Input")
    UInputAction* JumpAction;

    UPROPERTY(EditDefaultsOnly, Category="Input")
    UInputAction* InteractAction;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interaction")
    float InteractionDistance = 350.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Objectives")
    UJPObjectiveComponent* ObjectiveComponent;

private:
    void Move(const FInputActionValue& Value);
    void Look(const FInputActionValue& Value);
    void Interact();
};
