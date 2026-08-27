#include "JPWorldQueryLibrary.h"

#include "Editor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "LandscapeDataAccess.h"
#include "LandscapeEdit.h"
#include "LandscapeInfo.h"
#include "LandscapeProxy.h"
#include "Engine/Engine.h"
#include "Misc/Crc.h"

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

int32 UJPWorldQueryLibrary::GetLandscapeHeightAtXY(
    UObject* WorldContextObject,
    FVector2D WorldXY
)
{
    if (!WorldContextObject || !GEngine)
    {
        return -1;
    }

    UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
    if (!World)
    {
        return -1;
    }

    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
    {
        ++LandscapeCount;
        Landscape = *It;
    }
    if (LandscapeCount != 1 || !Landscape)
    {
        return -1;
    }

    const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(WorldXY.X, WorldXY.Y, 0.0));
    if (!Height.IsSet())
    {
        return -1;
    }

    return static_cast<int32>(FMath::RoundToFloat(Height.GetValue()));
}

int32 UJPWorldQueryLibrary::GetLandscapeRawHeightCRC(
    UObject* WorldContextObject
)
{
    if (!WorldContextObject || !GEngine)
    {
        UE_LOG(LogTemp, Error, TEXT("GetLandscapeRawHeightCRC: no world context or engine."));
        return -1;
    }

    UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
    if (!World)
    {
        UE_LOG(LogTemp, Error, TEXT("GetLandscapeRawHeightCRC: no world."));
        return -1;
    }

    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
    {
        ++LandscapeCount;
        Landscape = *It;
    }
    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("GetLandscapeRawHeightCRC: expected 1 landscape, found %d."), LandscapeCount);
        return -1;
    }

    ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
    if (!LandscapeInfo)
    {
        UE_LOG(LogTemp, Error, TEXT("GetLandscapeRawHeightCRC: LandscapeInfo is null."));
        return -1;
    }

    FIntRect Extent;
    if (!LandscapeInfo->GetLandscapeExtent(Landscape, Extent))
    {
        UE_LOG(LogTemp, Error, TEXT("GetLandscapeRawHeightCRC: GetLandscapeExtent failed."));
        return -1;
    }

    const int32 Width = Extent.Width() + 1;
    const int32 Height = Extent.Height() + 1;
    TArray<uint16> RawHeights;
    RawHeights.SetNumUninitialized(Width * Height);
    {
        FLandscapeEditDataInterface Edit(LandscapeInfo, false);
        Edit.GetHeightDataFast(Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y, RawHeights.GetData(), Width);
    }

    const uint32 RawCRC = FCrc::MemCrc32(RawHeights.GetData(), RawHeights.Num() * sizeof(uint16));
    UE_LOG(LogTemp, Display, TEXT("GetLandscapeRawHeightCRC: CRC=0x%08X pixels=%d extent=(%d,%d)-(%d,%d)"),
        RawCRC, RawHeights.Num(), Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y);
    return static_cast<int32>(RawCRC);
}
