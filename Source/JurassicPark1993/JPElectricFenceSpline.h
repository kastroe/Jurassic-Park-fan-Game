#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "JPElectricFenceSpline.generated.h"

class USceneComponent;
class USplineComponent;
class UStaticMesh;
class UStaticMeshComponent;

/**
 * Rigid modular electric-fence placement along a spline using adaptive module
 * selection (8m / 4m / 2m). It never deforms meshes.
 *
 * Placement semantics (validated simulator):
 *   At arc distance s, with P0 = spline world loc at s, T0 = yaw-only tangent at s:
 *     E = P0 + T0 * L            (predicted rigid-chord endpoint)
 *     P1 = spline world loc at s + L
 *     gap = distance(E, P1)
 *   Only lengths that fully fit within remaining are considered (8m, then 4m,
 *   then 2m). A candidate is chosen if its gap <= MaxGapThresholdCm; 2m is
 *   chosen whenever it fits (no gap condition). If nothing fits, stop and report
 *   the unused remainder. First module uses Start, last uses End, intermediates
 *   use Middle of the FINAL selected length. Never stretch/overhang/deform.
 */
UCLASS()
class JURASSICPARK1993_API AJP_ElectricFenceSpline : public AActor
{
    GENERATED_BODY()

public:
    AJP_ElectricFenceSpline();
    virtual void OnConstruction(const FTransform& Transform) override;

    UFUNCTION(BlueprintCallable, CallInEditor, Category = "JP|Electric Fence")
    void RebuildFence();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence")
    USceneComponent* SceneRoot;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence")
    USplineComponent* FenceSpline;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes")
    UStaticMesh* StartMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes")
    UStaticMesh* MiddleMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes")
    UStaticMesh* EndMesh;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes|4m")
    UStaticMesh* StartMesh4m;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes|4m")
    UStaticMesh* MiddleMesh4m;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes|4m")
    UStaticMesh* EndMesh4m;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes|2m")
    UStaticMesh* StartMesh2m;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes|2m")
    UStaticMesh* MiddleMesh2m;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence|Meshes|2m")
    UStaticMesh* EndMesh2m;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence")
    float ModuleLengthCm = 800.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "JP|Electric Fence")
    float MaxGapThresholdCm = 25.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    float LastSplineLengthCm = 0.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    int32 LastSectionCount = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    int32 LastCount8m = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    int32 LastCount4m = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    int32 LastCount2m = 0;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    float LastUnusedRemainderCm = 0.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    float LastWorstGapCm = 0.0f;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    TArray<float> LastSectionYaws;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    TArray<float> LastSectionLengthsCm;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "JP|Electric Fence|Diagnostics")
    TArray<float> LastSectionGapsCm;

private:
    UPROPERTY(Transient)
    TArray<UStaticMeshComponent*> GeneratedComponents;

    void ClearGeneratedComponents();
    float ComputeGapCm(float SplineDistanceCm, float LengthCm) const;
    UStaticMesh* SelectMiddleMesh(int32 LengthCm) const;
    UStaticMesh* SelectStartMesh(int32 LengthCm) const;
    UStaticMesh* SelectEndMesh(int32 LengthCm) const;
};
