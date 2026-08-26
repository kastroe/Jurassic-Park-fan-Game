#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "JPInteractable.generated.h"

UINTERFACE(BlueprintType)
class UJPInteractable : public UInterface
{
    GENERATED_BODY()
};

class JURASSICPARK1993_API IJPInteractable
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category="Interaction")
    void Interact(AActor* Interactor);
};
