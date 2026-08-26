#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "JPWorldQueryLibrary.generated.h"

UCLASS()
class JURASSICPARK1993_API UJPWorldQueryLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "JP|World Query", meta = (WorldContext = "WorldContextObject"))
    static bool GetWorldSurfaceZ(
        UObject* WorldContextObject,
        FVector2D WorldXY,
        float StartZ,
        float EndZ,
        float& OutZ
    );
};
