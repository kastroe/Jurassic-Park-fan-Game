#include "JPElectricFenceSpline.h"

#include "Components/SceneComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"

namespace JPElectricFence
{
	static constexpr int32 MiddleLength8m = 800;
	static constexpr int32 MiddleLength4m = 400;
	static constexpr int32 MiddleLength2m = 200;
}

AJP_ElectricFenceSpline::AJP_ElectricFenceSpline()
{
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
    RootComponent = SceneRoot;
    SceneRoot->SetMobility(EComponentMobility::Static);

    FenceSpline = CreateDefaultSubobject<USplineComponent>(TEXT("FenceSpline"));
    FenceSpline->SetupAttachment(SceneRoot);
    FenceSpline->SetMobility(EComponentMobility::Static);
    FenceSpline->bDrawDebug = true;
}

void AJP_ElectricFenceSpline::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    RebuildFence();
}

void AJP_ElectricFenceSpline::ClearGeneratedComponents()
{
    for (UStaticMeshComponent* Component : GeneratedComponents)
    {
        if (IsValid(Component))
        {
            Component->DestroyComponent();
        }
    }
    GeneratedComponents.Reset();
}

float AJP_ElectricFenceSpline::ComputeGapCm(float SplineDistanceCm, float LengthCm) const
{
    if (!FenceSpline)
    {
        return 0.0f;
    }

    const FVector P0 = FenceSpline->GetLocationAtDistanceAlongSpline(SplineDistanceCm, ESplineCoordinateSpace::World);
    FVector T0 = FenceSpline->GetTangentAtDistanceAlongSpline(SplineDistanceCm, ESplineCoordinateSpace::World);
    T0.Z = 0.0f;
    if (T0.IsNearlyZero())
    {
        T0 = FVector::ForwardVector;
    }
    T0 = T0.GetSafeNormal();

    const FVector P1 = FenceSpline->GetLocationAtDistanceAlongSpline(SplineDistanceCm + LengthCm, ESplineCoordinateSpace::World);
    const FVector Endpoint = P0 + T0 * LengthCm;
    return FVector::Dist(Endpoint, P1);
}

UStaticMesh* AJP_ElectricFenceSpline::SelectStartMesh(int32 LengthCm) const
{
    switch (LengthCm)
    {
    case JPElectricFence::MiddleLength8m: return StartMesh;
    case JPElectricFence::MiddleLength4m: return StartMesh4m;
    case JPElectricFence::MiddleLength2m: return StartMesh2m;
    default: break;
    }
    return nullptr;
}

UStaticMesh* AJP_ElectricFenceSpline::SelectMiddleMesh(int32 LengthCm) const
{
    switch (LengthCm)
    {
    case JPElectricFence::MiddleLength8m: return MiddleMesh;
    case JPElectricFence::MiddleLength4m: return MiddleMesh4m;
    case JPElectricFence::MiddleLength2m: return MiddleMesh2m;
    default: break;
    }
    return nullptr;
}

UStaticMesh* AJP_ElectricFenceSpline::SelectEndMesh(int32 LengthCm) const
{
    switch (LengthCm)
    {
    case JPElectricFence::MiddleLength8m: return EndMesh;
    case JPElectricFence::MiddleLength4m: return EndMesh4m;
    case JPElectricFence::MiddleLength2m: return EndMesh2m;
    default: break;
    }
    return nullptr;
}

void AJP_ElectricFenceSpline::RebuildFence()
{
    ClearGeneratedComponents();
    LastSectionYaws.Reset();
    LastSectionLengthsCm.Reset();
    LastSectionGapsCm.Reset();
    LastSectionCount = 0;
    LastCount8m = 0;
    LastCount4m = 0;
    LastCount2m = 0;
    LastUnusedRemainderCm = 0.0f;
    LastWorstGapCm = 0.0f;
    LastSplineLengthCm = FenceSpline ? FenceSpline->GetSplineLength() : 0.0f;

    if (!FenceSpline || LastSplineLengthCm <= KINDA_SMALL_NUMBER)
    {
        return;
    }

    const float GapThreshold = FMath::Max(MaxGapThresholdCm, 0.0f);
    const float Len8 = FMath::Max(ModuleLengthCm, 1.0f);
    const float Len4 = Len8 * 0.5f;
    const float Len2 = Len8 * 0.25f;

    if (!SelectStartMesh(JPElectricFence::MiddleLength8m) || !SelectMiddleMesh(JPElectricFence::MiddleLength8m) ||
        !SelectEndMesh(JPElectricFence::MiddleLength8m) ||
        !SelectStartMesh(JPElectricFence::MiddleLength4m) || !SelectMiddleMesh(JPElectricFence::MiddleLength4m) ||
        !SelectEndMesh(JPElectricFence::MiddleLength4m) ||
        !SelectStartMesh(JPElectricFence::MiddleLength2m) || !SelectMiddleMesh(JPElectricFence::MiddleLength2m) ||
        !SelectEndMesh(JPElectricFence::MiddleLength2m))
    {
        return;
    }

    // Pass 1: greedy adaptive selection of module lengths and their positions.
    TArray<float> Positions;
    TArray<int32> Lengths;
    TArray<float> Gaps;
    float s = 0.0f;
    while (true)
    {
        const float Remaining = LastSplineLengthCm - s;
        const bool bFit8 = Remaining >= Len8 - KINDA_SMALL_NUMBER;
        const bool bFit4 = Remaining >= Len4 - KINDA_SMALL_NUMBER;
        const bool bFit2 = Remaining >= Len2 - KINDA_SMALL_NUMBER;
        if (!bFit2)
        {
            LastUnusedRemainderCm = Remaining;
            break;
        }

        int32 ChosenLen = 0;
        float ChosenGap = 0.0f;

        if (bFit8)
        {
            const float Gap = ComputeGapCm(s, Len8);
            if (Gap <= GapThreshold)
            {
                ChosenLen = JPElectricFence::MiddleLength8m;
                ChosenGap = Gap;
            }
        }
        if (ChosenLen == 0 && bFit4)
        {
            const float Gap = ComputeGapCm(s, Len4);
            if (Gap <= GapThreshold)
            {
                ChosenLen = JPElectricFence::MiddleLength4m;
                ChosenGap = Gap;
            }
        }
        if (ChosenLen == 0 && bFit2)
        {
            ChosenLen = JPElectricFence::MiddleLength2m;
            ChosenGap = ComputeGapCm(s, Len2);
        }

        if (ChosenLen == 0)
        {
            LastUnusedRemainderCm = Remaining;
            break;
        }

        Positions.Add(s);
        Lengths.Add(ChosenLen);
        Gaps.Add(ChosenGap);
        s += ChosenLen;
    }

    const int32 SectionCount = Lengths.Num();
    LastSectionCount = SectionCount;
    if (SectionCount == 0)
    {
        return;
    }

    // Pass 2: place modules with roles (Start / Middle / End of final length).
    for (int32 Index = 0; Index < SectionCount; ++Index)
    {
        const float Position = Positions[Index];
        const int32 Len = Lengths[Index];
        UStaticMesh* Mesh = SelectMiddleMesh(Len);
        if (Index == 0)
        {
            Mesh = SelectStartMesh(Len);
        }
        else if (Index == SectionCount - 1)
        {
            Mesh = SelectEndMesh(Len);
        }
        if (!Mesh)
        {
            continue;
        }

        const FVector Location = FenceSpline->GetLocationAtDistanceAlongSpline(Position, ESplineCoordinateSpace::World);
        FVector Tangent = FenceSpline->GetTangentAtDistanceAlongSpline(Position, ESplineCoordinateSpace::World);
        Tangent.Z = 0.0f;
        if (Tangent.IsNearlyZero())
        {
            Tangent = FVector::ForwardVector;
        }
        const FRotator Rotation = FRotationMatrix::MakeFromX(Tangent.GetSafeNormal()).Rotator();

        UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(this, NAME_None, RF_Transactional);
        Component->SetStaticMesh(Mesh);
        Component->SetMobility(EComponentMobility::Static);
        Component->SetupAttachment(SceneRoot);
        Component->RegisterComponent();
        Component->SetWorldLocationAndRotation(Location, Rotation);
        GeneratedComponents.Add(Component);

        LastSectionYaws.Add(Rotation.Yaw);
        LastSectionLengthsCm.Add(static_cast<float>(Len));
        LastSectionGapsCm.Add(Gaps[Index]);
        LastWorstGapCm = FMath::Max(LastWorstGapCm, Gaps[Index]);

        if (Len == JPElectricFence::MiddleLength8m)
        {
            ++LastCount8m;
        }
        else if (Len == JPElectricFence::MiddleLength4m)
        {
            ++LastCount4m;
        }
        else
        {
            ++LastCount2m;
        }
    }
}
