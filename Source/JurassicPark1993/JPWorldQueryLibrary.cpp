#include "JPWorldQueryLibrary.h"

#include "Engine/World.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "Engine/Engine.h"

bool UJPWorldQueryLibrary::GetWorldSurfaceZ(
    UObject* WorldContextObject,
    FVector2D WorldXY,
    float StartZ,
    float EndZ,
    float& OutZ
)
{
    OutZ = 0.0f;
    if (!WorldContextObject || !GEngine)
    {
        return false;
    }

    UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
    if (!World)
    {
        return false;
    }

    const FVector Start(WorldXY.X, WorldXY.Y, StartZ);
    const FVector End(WorldXY.X, WorldXY.Y, EndZ);
    FCollisionQueryParams QueryParams(SCENE_QUERY_STAT(JPWorldSurfaceZ), true);
    TArray<FHitResult> Hits;

    if (!World->LineTraceMultiByChannel(Hits, Start, End, ECC_Visibility, QueryParams))
    {
        return false;
    }

    for (const FHitResult& Hit : Hits)
    {
        AActor* HitActor = Hit.GetActor();
        UPrimitiveComponent* HitComponent = Hit.GetComponent();
        const bool bLandscapeActor = HitActor && HitActor->IsA<ALandscapeProxy>();
        const bool bLandscapeComponent = HitComponent && HitComponent->IsA<ULandscapeComponent>();
        if ((bLandscapeActor || bLandscapeComponent) && Hit.bBlockingHit)
        {
            OutZ = Hit.ImpactPoint.Z;
            return true;
        }
    }

    return false;
}
