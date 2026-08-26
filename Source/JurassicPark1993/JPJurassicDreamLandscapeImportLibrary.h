#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "JPJurassicDreamLandscapeImportLibrary.generated.h"

UCLASS()
class JURASSICPARK1993_API UJPJurassicDreamLandscapeImportLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Landscape")
    static bool ImportJurassicDreamTerrain();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Markers")
    static bool AssignTempMarkerFolders();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Markers")
    static bool SnapTempMarkersToLandscape();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool ProbeJP1993Heights(const FString& CsvPoints);

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool SpawnJP1993Markers(const FString& CsvPoints);

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool CreateTourRoadGuide();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool FixTourRoadGuideCentralRidge();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool EnhanceTourRoadVisualization();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool FixTourRoadCusps();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool FlattenTourRoadCuspsTangents();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool ProbeTourRoadWaterCrossing();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool FixTourRoadWaterCrossing();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Layout")
    static bool BuildTourRoadVisualPass();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Landscape")
    static bool ProbeTourRoadGrading();

    UFUNCTION(BlueprintCallable, Category = "JP|Jurassic Dream|Landscape")
    static bool GradeTourRoadLandscape();
};
