#include "JPTourVehicle.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SplineComponent.h"

AJPTourVehicle::AJPTourVehicle()
{
    PrimaryActorTick.bCanEverTick = true;
    VehicleMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VehicleMesh"));
    RootComponent = VehicleMesh;
}

void AJPTourVehicle::SetRoute(USplineComponent* InRoute)
{
    Route = InRoute;
    DistanceAlongSpline = 0.0f;
}

void AJPTourVehicle::StartTour()
{
    bTourRunning = true;
}

void AJPTourVehicle::StopTour()
{
    bTourRunning = false;
}

void AJPTourVehicle::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    if (!bTourRunning || !Route) return;

    const float Length = Route->GetSplineLength();
    DistanceAlongSpline += SpeedCmPerSecond * DeltaSeconds;

    if (DistanceAlongSpline >= Length)
    {
        if (bLoopRoute) DistanceAlongSpline = FMath::Fmod(DistanceAlongSpline, Length);
        else
        {
            DistanceAlongSpline = Length;
            bTourRunning = false;
        }
    }

    const FVector Location = Route->GetLocationAtDistanceAlongSpline(DistanceAlongSpline, ESplineCoordinateSpace::World);
    const FRotator Rotation = Route->GetRotationAtDistanceAlongSpline(DistanceAlongSpline, ESplineCoordinateSpace::World);
    SetActorLocationAndRotation(Location, Rotation);
}
