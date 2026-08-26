#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "JPTourVehicle.generated.h"

class UStaticMeshComponent;
class USplineComponent;

UCLASS()
class JURASSICPARK1993_API AJPTourVehicle : public APawn
{
    GENERATED_BODY()

public:
    AJPTourVehicle();
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Tour")
    void StartTour();

    UFUNCTION(BlueprintCallable, Category="Tour")
    void StopTour();

    UFUNCTION(BlueprintCallable, Category="Tour")
    void SetRoute(USplineComponent* InRoute);

protected:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly)
    UStaticMeshComponent* VehicleMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Tour")
    float SpeedCmPerSecond = 700.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Tour")
    bool bLoopRoute = false;

private:
    UPROPERTY()
    USplineComponent* Route;

    float DistanceAlongSpline = 0.0f;
    bool bTourRunning = false;
};
