#include "JPJurassicDreamLandscapeImportLibrary.h"

#if WITH_EDITOR

#include "Editor.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextRenderActor.h"
#include "Components/TextRenderComponent.h"
#include "Components/SplineComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "Landscape.h"
#include "LandscapeDataAccess.h"
#include "LandscapeEdit.h"
#include "LandscapeInfo.h"
#include "LandscapeProxy.h"
#include "Materials/MaterialInterface.h"
#include "Misc/Crc.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
    const TCHAR* const TargetMapPackage = TEXT("/Game/Maps/JP_JurassicDream_Terrain_Test");
    const TCHAR* const HeightmapRelativePath = TEXT("Reference/JurassicDreamTerrain/JurassicDream_4081x4081_UE.r16");
    constexpr int32 HeightmapResolution = 4081;
    constexpr int32 HeightmapQuads = 4080;
    constexpr int32 HeightmapBytes = HeightmapResolution * HeightmapResolution * sizeof(uint16);
}

bool UJPJurassicDreamLandscapeImportLibrary::ImportJurassicDreamTerrain()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel)
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import refused: no editor world is loaded."));
        return false;
    }

    if (World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import refused: active map is %s, expected %s."),
            *World->GetOutermost()->GetName(), TargetMapPackage);
        return false;
    }

    for (TActorIterator<ALandscapeProxy> It(World); It; ++It)
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import refused: a Landscape already exists in the target map."));
        return false;
    }

    const FString HeightmapPath = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / HeightmapRelativePath);
    TArray<uint8> RawHeightmap;
    if (!FFileHelper::LoadFileToArray(RawHeightmap, *HeightmapPath) || RawHeightmap.Num() != HeightmapBytes)
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import refused: expected %d bytes at %s, found %d."),
            HeightmapBytes, *HeightmapPath, RawHeightmap.Num());
        return false;
    }

    TArray<uint16> HeightData;
    HeightData.SetNumUninitialized(HeightmapResolution * HeightmapResolution);
    for (int32 Index = 0; Index < HeightData.Num(); ++Index)
    {
        const int32 ByteIndex = Index * sizeof(uint16);
        HeightData[Index] = static_cast<uint16>(RawHeightmap[ByteIndex]) |
            (static_cast<uint16>(RawHeightmap[ByteIndex + 1]) << 8);
    }

    ALandscape* Landscape = World->SpawnActor<ALandscape>(ALandscape::StaticClass(), FTransform::Identity);
    if (!Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import failed: could not spawn ALandscape."));
        return false;
    }

    Landscape->SetActorLabel(TEXT("JP_JurassicDream_Terrain"));
    Landscape->SetActorScale3D(FVector(100.3921569f, 100.3921569f, 200.0030518f));
    Landscape->SetActorLocation(FVector(0.0f, 0.0f, 51200.7813f));

    const FGuid LandscapeGuid = FGuid::NewGuid();
    const FGuid FinalLayerGuid;

    TMap<FGuid, TArray<uint16>> ImportHeightData;
    ImportHeightData.Add(FinalLayerGuid, MoveTemp(HeightData));
    TMap<FGuid, TArray<FLandscapeImportLayerInfo>> ImportMaterialLayerInfos;
    ImportMaterialLayerInfos.Add(FinalLayerGuid, TArray<FLandscapeImportLayerInfo>());
    const TArrayView<const FLandscapeLayer> ImportLayers;

    Landscape->Import(
        LandscapeGuid,
        0,
        0,
        HeightmapQuads,
        HeightmapQuads,
        1,
        255,
        ImportHeightData,
        nullptr,
        ImportMaterialLayerInfos,
        ELandscapeImportAlphamapType::Additive,
        ImportLayers);

    Landscape->PostEditChange();
    Landscape->RegisterAllComponents();

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("Jurassic Dream import failed: could not save the target level."));
        return false;
    }

    UE_LOG(LogTemp, Display, TEXT("JURASSIC DREAM LANDSCAPE IMPORTED: 4081x4081, 16x16 components, 255 quads/component."));
    return true;
}

namespace
{
    const TPair<const TCHAR*, const TCHAR*> MarkerFolderRules[] = {
        { TEXT("MRKL_ROAD_"), TEXT("TEMP_Markers/Roads") },
        { TEXT("MRK_ROAD_"), TEXT("TEMP_Markers/Roads") },
        { TEXT("MRKL_GATE_"), TEXT("TEMP_Markers/Gates") },
        { TEXT("MRK_GATE_"), TEXT("TEMP_Markers/Gates") },
        { TEXT("MRKL_BRIDGE_"), TEXT("TEMP_Markers/Bridge") },
        { TEXT("MRK_BRIDGE_"), TEXT("TEMP_Markers/Bridge") },
        { TEXT("MRKL_JEEP_"), TEXT("TEMP_Markers/Vehicles") },
        { TEXT("MRK_JEEP_"), TEXT("TEMP_Markers/Vehicles") },
        { TEXT("MRK_SPAWN_"), TEXT("TEMP_Markers/Arrival") },
        { TEXT("MRKL_SPAWN_"), TEXT("TEMP_Markers/Arrival") },
        { TEXT("MRK_TREXPAD_"), TEXT("TEMP_Markers/Fences/TrexPaddock") },
        { TEXT("MRK_FENCE_"), TEXT("TEMP_Markers/Fences") },
    };
}

bool UJPJurassicDreamLandscapeImportLibrary::AssignTempMarkerFolders()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker folders refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker folders refused: target map is not active."));
        return false;
    }

    int32 TotalAssigned = 0;
    for (FActorIterator It(World); It; ++It)
    {
        AActor* Actor = *It;
        const FString Label = Actor->GetActorLabel();
        for (const TPair<const TCHAR*, const TCHAR*>& Rule : MarkerFolderRules)
        {
            if (Label.StartsWith(Rule.Key))
            {
                Actor->SetFolderPath(FName(Rule.Value));
                ++TotalAssigned;
                break;
            }
        }
    }

    if (TotalAssigned == 0)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker folders failed: no MRK_* actors found in the target map."));
        return false;
    }

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("Marker folders failed: could not save the target level."));
        return false;
    }

    UE_LOG(LogTemp, Display, TEXT("JURASSIC DREAM MARKER FOLDERS ASSIGNED: %d actors."), TotalAssigned);
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::SnapTempMarkersToLandscape()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker snap refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker snap refused: target map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    TArray<AActor*> Markers;
    TMap<FString, AActor*> LabelsBySuffix;

    for (FActorIterator It(World); It; ++It)
    {
        AActor* Actor = *It;
        const FString Label = Actor->GetActorLabel();

        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(Actor))
        {
            ++LandscapeCount;
            Landscape = Proxy;
            continue;
        }

        if (Label.StartsWith(TEXT("MRKL_")))
        {
            LabelsBySuffix.Add(Label.Mid(5), Actor);
        }
        else if (Label.StartsWith(TEXT("MRK_")))
        {
            Markers.Push(Actor);
        }
    }

    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker snap refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
        return false;
    }

    if (Markers.Num() == 0)
    {
        UE_LOG(LogTemp, Error, TEXT("Marker snap refused: no MRK_* markers found."));
        return false;
    }

    int32 Snapped = 0;
    int32 NoHit = 0;
    int32 Adjusted = 0;
    double MinCorr = TNumericLimits<double>::Max();
    double MaxCorr = TNumericLimits<double>::Lowest();

    for (AActor* Marker : Markers)
    {
        const FVector Loc = Marker->GetActorLocation();

        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Loc.X, Loc.Y, Loc.Z));
        if (!Height.IsSet())
        {
            UE_LOG(LogTemp, Warning, TEXT("JPSNAP NO_HIT: %s"), *Marker->GetActorLabel());
            ++NoHit;
            continue;
        }

        const float NewZ = Height.GetValue() + 100.0f;
        const double Correction = static_cast<double>(NewZ) - static_cast<double>(Loc.Z);
        if (FMath::Abs(Correction) > 0.5)
        {
            ++Adjusted;
        }
        MinCorr = FMath::Min(MinCorr, Correction);
        MaxCorr = FMath::Max(MaxCorr, Correction);

        Marker->SetActorLocation(FVector(Loc.X, Loc.Y, NewZ));

        if (AActor** LabelPtr = LabelsBySuffix.Find(Marker->GetActorLabel().Mid(4)))
        {
            (*LabelPtr)->SetActorLocation(FVector(Loc.X, Loc.Y, NewZ + 300.0f));
        }

        ++Snapped;
    }

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("Marker snap failed: could not save the target level."));
        return false;
    }

    UE_LOG(LogTemp, Display,
        TEXT("JURASSIC DREAM MARKER SNAP: SNAPPED=%d ADJUSTED=%d NO_HIT=%d MIN_DZ=%.2f MAX_DZ=%.2f"),
        Snapped, Adjusted, NoHit, MinCorr, MaxCorr);
    return true;
}

namespace
{
    struct FJP93Point
    {
        FString Name;
        FString Label;
        double X = 0.0;
        double Y = 0.0;
        double Lift = 400.0;
    };

    bool ParseJP93Csv(const FString& Csv, TArray<FJP93Point>& OutPoints)
    {
        TArray<FString> Entries;
        Csv.ParseIntoArray(Entries, TEXT(";"), true);
        for (const FString& Entry : Entries)
        {
            TArray<FString> Fields;
            Entry.ParseIntoArray(Fields, TEXT(","), true);
            if (Fields.Num() < 3)
            {
                return false;
            }
            FJP93Point Point;
            Point.Name = Fields[0].TrimStartAndEnd();
            Point.Label = Fields[0].TrimStartAndEnd();
            Point.X = FCString::Atod(*Fields[1]);
            Point.Y = FCString::Atod(*Fields[2]);
            if (Fields.Num() >= 4)
            {
                Point.Lift = FCString::Atod(*Fields[3]);
            }
            OutPoints.Push(MoveTemp(Point));
        }
        return OutPoints.Num() > 0;
    }

    bool GetTargetWorldForJP93(UWorld*& OutWorld, ALandscapeProxy*& OutLandscape)
    {
        if (!GEditor)
        {
            UE_LOG(LogTemp, Error, TEXT("JP1993 refused: editor is unavailable."));
            return false;
        }
        OutWorld = GEditor->GetEditorWorldContext().World();
        if (!OutWorld || !OutWorld->PersistentLevel || OutWorld->GetOutermost()->GetName() != TargetMapPackage)
        {
            UE_LOG(LogTemp, Error, TEXT("JP1993 refused: target map is not active."));
            return false;
        }
        int32 LandscapeCount = 0;
        for (TActorIterator<ALandscapeProxy> It(OutWorld); It; ++It)
        {
            ++LandscapeCount;
            OutLandscape = *It;
        }
        if (LandscapeCount != 1 || !OutLandscape)
        {
            UE_LOG(LogTemp, Error, TEXT("JP1993 refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
            return false;
        }
        return true;
    }
}

bool UJPJurassicDreamLandscapeImportLibrary::ProbeJP1993Heights(const FString& CsvPoints)
{
    UWorld* World = nullptr;
    ALandscapeProxy* Landscape = nullptr;
    if (!GetTargetWorldForJP93(World, Landscape))
    {
        return false;
    }

    TArray<FJP93Point> Points;
    if (!ParseJP93Csv(CsvPoints, Points))
    {
        UE_LOG(LogTemp, Error, TEXT("JP1993 probe refused: bad CSV."));
        return false;
    }

    for (const FJP93Point& Point : Points)
    {
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Point.X, Point.Y, 0.0));
        if (Height.IsSet())
        {
            UE_LOG(LogTemp, Display, TEXT("JP1993_PROBE %s|X=%.1f|Y=%.1f|HEIGHT=%.2f|SET=1"),
                *Point.Name, Point.X, Point.Y, static_cast<double>(Height.GetValue()));
        }
        else
        {
            UE_LOG(LogTemp, Display, TEXT("JP1993_PROBE %s|X=%.1f|Y=%.1f|HEIGHT=0.00|SET=0"),
                *Point.Name, Point.X, Point.Y);
        }
    }

    UE_LOG(LogTemp, Display, TEXT("JP1993 PROBE COMPLETE: %d points."), Points.Num());
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::SpawnJP1993Markers(const FString& CsvPoints)
{
    UWorld* World = nullptr;
    ALandscapeProxy* Landscape = nullptr;
    if (!GetTargetWorldForJP93(World, Landscape))
    {
        return false;
    }

    TArray<FJP93Point> Points;
    if (!ParseJP93Csv(CsvPoints, Points))
    {
        UE_LOG(LogTemp, Error, TEXT("JP1993 spawn refused: bad CSV."));
        return false;
    }

    int32 Existing = 0;
    for (FActorIterator It(World); It; ++It)
    {
        if (It->GetActorLabel().StartsWith(TEXT("JP93_")))
        {
            ++Existing;
        }
    }
    if (Existing > 0)
    {
        UE_LOG(LogTemp, Error, TEXT("JP1993 spawn refused: %d JP93_* actors already exist."), Existing);
        return false;
    }

    UObject* SphereMesh = StaticLoadObject(UStaticMesh::StaticClass(), nullptr, TEXT("/Engine/BasicShapes/Sphere"));
    if (!SphereMesh)
    {
        UE_LOG(LogTemp, Error, TEXT("JP1993 spawn failed: missing sphere mesh."));
        return false;
    }

    UMaterial* Material = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
    if (!Material)
    {
        UE_LOG(LogTemp, Warning, TEXT("JP1993: MK_JP1993 material not found; markers use default material."));
    }

    constexpr float MarkerScale = 15.0f;

    int32 Spawned = 0;
    for (const FJP93Point& Point : Points)
    {
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Point.X, Point.Y, 0.0));
        if (!Height.IsSet())
        {
            UE_LOG(LogTemp, Warning, TEXT("JP1993 SKIP_NO_TERRAIN: %s"), *Point.Name);
            continue;
        }

        const FVector Location(Point.X, Point.Y, Height.GetValue() + Point.Lift);
        AActor* Marker = World->SpawnActor<AStaticMeshActor>(
            AStaticMeshActor::StaticClass(), FTransform(FRotator::ZeroRotator, Location));
        if (!Marker)
        {
            continue;
        }

        UStaticMeshComponent* MeshComp = Cast<AStaticMeshActor>(Marker)->GetStaticMeshComponent();
        if (MeshComp)
        {
            MeshComp->SetStaticMesh(Cast<UStaticMesh>(SphereMesh));
            MeshComp->SetWorldScale3D(FVector(MarkerScale));
            if (Material)
            {
                MeshComp->SetMaterial(0, Material);
            }
        }
        Marker->SetActorLabel(FString::Printf(TEXT("JP93_%s"), *Point.Name.Replace(TEXT(" "), TEXT(""))));
        Marker->SetFolderPath(FName(TEXT("JP1993_Layout")));

        ATextRenderActor* TextRender = World->SpawnActor<ATextRenderActor>(
            ATextRenderActor::StaticClass(),
            FTransform(FRotator(0.0f, 180.0f, 0.0f), Location + FVector(0, 0, 2600)));
        if (TextRender)
        {
            if (UTextRenderComponent* TextComp = TextRender->GetTextRender())
            {
                TextComp->SetText(FText::FromString(Point.Label));
                TextComp->SetWorldSize(1600.0f);
                TextComp->SetTextRenderColor(FColor(255, 235, 140));
            }
            TextRender->SetActorLabel(FString::Printf(TEXT("JP93L_%s"), *Point.Name.Replace(TEXT(" "), TEXT(""))));
            TextRender->SetFolderPath(FName(TEXT("JP1993_Layout/Labels")));
        }

        ++Spawned;
    }

    if (Spawned != Points.Num())
    {
        UE_LOG(LogTemp, Warning, TEXT("JP1993 spawned %d of %d requested markers."), Spawned, Points.Num());
    }

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("JP1993 failed: could not save the target level."));
        return false;
    }

    UE_LOG(LogTemp, Display, TEXT("JURASSIC PARK 1993 LAYOUT MARKERS SPAWNED: %d."), Spawned);
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::CreateTourRoadGuide()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("TourRoad guide refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("TourRoad guide refused: target map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    TMap<FString, AActor*> JP93Map;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It))
        {
            ++LandscapeCount;
            Landscape = Proxy;
        }
        else
        {
            const FString Label = It->GetActorLabel();
            if (Label.StartsWith(TEXT("JP93_")))
            {
                JP93Map.Add(Label, *It);
            }
            if (Label.StartsWith(TEXT("TOUR_")))
            {
                UE_LOG(LogTemp, Error, TEXT("TourRoad guide refused: TOUR_* guide already exists (%s)."), *Label);
                return false;
            }
        }
    }

    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("TourRoad guide refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
        return false;
    }

    const TArray<FString> RouteLabels = {
        TEXT("JP93_VisitorCenter"),
        TEXT("JP93_MainGate"),
        TEXT("JP93_Brachiosaurus"),
        TEXT("JP93_Gallimimus"),
        TEXT("JP93_Triceratops"),
        TEXT("JP93_T-RexPaddock"),
        TEXT("JP93_Dilophosaurus"),
    };

    TArray<FVector> Anchors;
    for (const FString& Lbl : RouteLabels)
    {
        AActor** Found = JP93Map.Find(Lbl);
        if (!Found)
        {
            UE_LOG(LogTemp, Error, TEXT("TourRoad guide refused: missing anchor %s."), *Lbl);
            return false;
        }
        Anchors.Add((*Found)->GetActorLocation());
    }

    // Build sampled points along each segment, sampling terrain height
    constexpr double IntervalCm = 2500.0;
    constexpr double HeightOffsetCm = 80.0;
    TArray<FVector> Sampled;
    Sampled.Reserve(512);
    double TotalLengthCm = 0.0;
    int32 NoHitCount = 0;

    struct FSegmentReport
    {
        FString From;
        FString To;
        double HorizCm = 0;
        double DeltaZ = 0;
        double SlopeDeg = 0;
    };
    TArray<FSegmentReport> SegmentReports;
    SegmentReports.Reserve(RouteLabels.Num());

    auto SampleHeight = [&](double X, double Y, double& OutZ) -> bool
    {
        const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
        if (!H.IsSet()) return false;
        OutZ = static_cast<double>(H.GetValue());
        return true;
    };

    // Pre-sample anchor heights for segment reports
    TArray<double> AnchorHeights;
    for (const FVector& A : Anchors)
    {
        double Hz = 0;
        if (!SampleHeight(A.X, A.Y, Hz))
        {
            UE_LOG(LogTemp, Error, TEXT("TourRoad guide refused: anchor at %.0f,%.0f has no landscape height."), A.X, A.Y);
            return false;
        }
        AnchorHeights.Add(Hz);
    }

    for (int32 Seg = 0; Seg < Anchors.Num(); ++Seg)
    {
        const FVector& A = Anchors[Seg];
        const FVector& B = Anchors[(Seg + 1) % Anchors.Num()];
        const double HAz = AnchorHeights[Seg];
        const double HBz = AnchorHeights[(Seg + 1) % AnchorHeights.Num()];
        const double Horiz = FVector2D::Distance(FVector2D(A.X, A.Y), FVector2D(B.X, B.Y));
        const double DeltaZ = HBz - HAz;
        const double SlopeDeg = (Horiz > 1e-6) ? FMath::Atan2(FMath::Abs(DeltaZ), Horiz) * 180.0 / PI : 0.0;
        SegmentReports.Add({ RouteLabels[Seg], RouteLabels[(Seg + 1) % RouteLabels.Num()], Horiz, DeltaZ, SlopeDeg });

        const int32 Steps = FMath::Max(1, FMath::CeilToInt(Horiz / IntervalCm));
        for (int32 s = 0; s < Steps; ++s)
        {
            const double T = static_cast<double>(s) / static_cast<double>(Steps);
            const double X = FMath::Lerp(A.X, B.X, T);
            const double Y = FMath::Lerp(A.Y, B.Y, T);
            double Hz = 0;
            if (!SampleHeight(X, Y, Hz))
            {
                ++NoHitCount;
                continue;
            }
            const FVector P(X, Y, Hz + HeightOffsetCm);
            if (Sampled.Num() > 0)
            {
                TotalLengthCm += FVector::Dist(Sampled.Last(), P);
            }
            Sampled.Add(P);
        }
    }
    // Close the loop with final anchor point
    {
        double Hz = 0;
        SampleHeight(Anchors[0].X, Anchors[0].Y, Hz);
        const FVector P(Anchors[0].X, Anchors[0].Y, Hz + HeightOffsetCm);
        if (Sampled.Num() > 0)
        {
            TotalLengthCm += FVector::Dist(Sampled.Last(), P);
        }
        Sampled.Add(P);
    }

    // Report before saving
    UE_LOG(LogTemp, Display, TEXT("JPTOUR TOTAL_LENGTH=%.1f cm (%.3f km) POINTS=%d NO_HIT_SAMPLES=%d"), TotalLengthCm, TotalLengthCm / 100000.0, Sampled.Num(), NoHitCount);
    for (int32 i = 0; i < SegmentReports.Num(); ++i)
    {
        const FSegmentReport& R = SegmentReports[i];
        const bool bExtreme = (FMath::Abs(R.SlopeDeg) > 15.0) || (FMath::Abs(R.DeltaZ) > 6000.0);
        UE_LOG(LogTemp, Display, TEXT("JPTOUR SEG %d: %s -> %s HORIZ=%.0f cm DELTA_Z=%.0f cm SLOPE=%.1f deg%s"),
            i, *R.From, *R.To, R.HorizCm, R.DeltaZ, R.SlopeDeg, bExtreme ? TEXT(" EXTREME") : TEXT(""));
    }
    if (NoHitCount > 0)
    {
        UE_LOG(LogTemp, Warning, TEXT("JPTOUR WARNING: %d sampled points had no landscape height (outside terrain)."), NoHitCount);
    }

    // Create spline actor
    AActor* GuideActor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity);
    if (!GuideActor)
    {
        UE_LOG(LogTemp, Error, TEXT("TourRoad guide failed: could not spawn guide actor."));
        return false;
    }
    GuideActor->SetActorLabel(TEXT("TOUR_RoadGuide"));
    GuideActor->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide")));

    USceneComponent* Root = NewObject<USceneComponent>(GuideActor, TEXT("Root"));
    Root->RegisterComponent();
    GuideActor->SetRootComponent(Root);
    GuideActor->AddInstanceComponent(Root);

    USplineComponent* Spline = NewObject<USplineComponent>(GuideActor, TEXT("TourSpline"));
    Spline->SetupAttachment(Root);
    Spline->SetClosedLoop(true);
    Spline->ClearSplinePoints(false);
    for (int32 i = 0; i < Sampled.Num(); ++i)
    {
        Spline->AddSplinePoint(Sampled[i], ESplineCoordinateSpace::World, false);
        Spline->SetSplinePointType(i, ESplinePointType::Curve, false);
    }
    Spline->UpdateSpline();
    Spline->RegisterComponent();
    GuideActor->AddInstanceComponent(Spline);

    // Also add small visible segment spheres every ~4th point for Lit-mode visibility
    UObject* SphereMesh = StaticLoadObject(UStaticMesh::StaticClass(), nullptr, TEXT("/Engine/BasicShapes/Sphere"));
    UMaterial* RoadMat = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
    if (!RoadMat)
    {
        RoadMat = LoadObject<UMaterial>(nullptr, TEXT("/Engine/EngineMaterials/WorldGridMaterial"));
    }
    int32 SphereCount = 0;
    for (int32 i = 0; i < Sampled.Num(); i += 4)
    {
        AActor* Seg = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator::ZeroRotator, Sampled[i]));
        if (!Seg) continue;
        if (UStaticMeshComponent* SMC = Cast<AStaticMeshActor>(Seg)->GetStaticMeshComponent())
        {
            SMC->SetStaticMesh(Cast<UStaticMesh>(SphereMesh));
            SMC->SetWorldScale3D(FVector(0.9f));
            if (RoadMat) SMC->SetMaterial(0, RoadMat);
        }
        Seg->SetActorLabel(FString::Printf(TEXT("TOUR_Seg_%03d"), SphereCount));
        Seg->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide/Segments")));
        ++SphereCount;
    }
    UE_LOG(LogTemp, Display, TEXT("JPTOUR SPHERES=%d SPLINE_POINTS=%d"), SphereCount, Sampled.Num());

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("TourRoad guide failed: could not save the target level."));
        return false;
    }

    UE_LOG(LogTemp, Display, TEXT("JURASSIC PARK TOUR ROAD GUIDE CREATED: %.3f km, %d spline points, %d segment spheres."), TotalLengthCm / 100000.0, Sampled.Num(), SphereCount);
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::FixTourRoadGuideCentralRidge()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("FixTourRoad refused: editor is unavailable."));
        return false;
    }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("FixTourRoad refused: target map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    TMap<FString, AActor*> JP93Map;
    TArray<AActor*> ExistingTour;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It))
        {
            ++LandscapeCount;
            Landscape = Proxy;
        }
        else
        {
            const FString L = It->GetActorLabel();
            if (L.StartsWith(TEXT("JP93_")))
            {
                JP93Map.Add(L, *It);
            }
            if (L.StartsWith(TEXT("TOUR_")))
            {
                ExistingTour.Add(*It);
            }
        }
    }
    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("FixTourRoad refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
        return false;
    }
    if (ExistingTour.Num() == 0)
    {
        UE_LOG(LogTemp, Error, TEXT("FixTourRoad refused: no existing TOUR_* guide to update. Create one first."));
        return false;
    }

    // Clockwise loop sorted angularly around island center (204800,204800) - no self-intersection by construction
    const TArray<FString> RouteLabels = {
        TEXT("JP93_VisitorCenter"),
        TEXT("JP93_T-RexPaddock"),
        TEXT("JP93_Brachiosaurus"),
        TEXT("JP93_Gallimimus"),
        TEXT("JP93_Triceratops"),
        TEXT("JP93_Dilophosaurus"),
        TEXT("JP93_MainGate"),
    };
    TArray<FVector> Anchors;
    for (const FString& Lbl : RouteLabels)
    {
        AActor** F = JP93Map.Find(Lbl);
        if (!F)
        {
            UE_LOG(LogTemp, Error, TEXT("FixTourRoad refused: missing anchor %s."), *Lbl);
            return false;
        }
        Anchors.Add((*F)->GetActorLocation());
    }

    auto SampleHeight = [&](double X, double Y, double& OutZ) -> bool
    {
        const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
        if (!H.IsSet()) return false;
        OutZ = static_cast<double>(H.GetValue());
        return true;
    };

    struct FWaypointInfo { FVector Pos; double Height; FString Name; };
    // Per-segment best for both signs
    struct FOpt { FVector Pos; double Height; bool bValid=false; };
    TArray<FOpt> BestPos, BestNeg;
    BestPos.SetNum(Anchors.Num()); BestNeg.SetNum(Anchors.Num());
    auto FindBestWithSign = [&](const FVector& A, const FVector& B, double Sign, FVector& OutWP, double& OutH)->bool{
        double HA=0,HB=0; if(!SampleHeight(A.X,A.Y,HA)||!SampleHeight(B.X,B.Y,HB)) return false;
        const FVector Mid((A.X+B.X)*0.5,(A.Y+B.Y)*0.5,0);
        const FVector Dir(B.X-A.X,B.Y-A.Y,0);
        const double Len=FVector2D::Distance(FVector2D(A.X,A.Y),FVector2D(B.X,B.Y)); if(Len<1e-6) return false;
        const FVector Perp(-Dir.Y/Len, Dir.X/Len,0);
        const TArray<double> Offs={10000,15000,20000,30000,40000,50000};
        double BestSlope=1e9,BestLen=1e9; bool bFound=false; FVector BestWP; double BestHW=0;
        for(double Off:Offs){
            const double X=Mid.X+Perp.X*Off*Sign, Y=Mid.Y+Perp.Y*Off*Sign;
            if(X<0||X>409600||Y<0||Y>409600) continue;
            double HW=0; if(!SampleHeight(X,Y,HW)) continue;
            const double d1=FVector2D::Distance(FVector2D(A.X,A.Y),FVector2D(X,Y));
            const double d2=FVector2D::Distance(FVector2D(X,Y),FVector2D(B.X,B.Y));
            if(d1<1e-6||d2<1e-6) continue;
            const double s1=FMath::Atan2(FMath::Abs(HW-HA),d1)*180.0/PI;
            const double s2=FMath::Atan2(FMath::Abs(HB-HW),d2)*180.0/PI;
            const double MaxSlope=FMath::Max(s1,s2); const double Tot=d1+d2;
            if(MaxSlope<BestSlope-0.01 || (FMath::IsNearlyEqual(MaxSlope,BestSlope,0.1) && Tot<BestLen)){
                BestSlope=MaxSlope; BestLen=Tot; BestWP=FVector(X,Y,HW); BestHW=HW; bFound=true;
            }
        }
        if(!bFound) return false; OutWP=BestWP; OutH=BestHW; return true;
    };
    for(int32 Seg=0; Seg<Anchors.Num(); ++Seg){
        const FVector &A=Anchors[Seg], &B=Anchors[(Seg+1)%Anchors.Num()];
        FVector WP; double WH;
        if(FindBestWithSign(A,B, 1.0, WP,WH)) BestPos[Seg]={WP,WH,true};
        if(FindBestWithSign(A,B,-1.0, WP,WH)) BestNeg[Seg]={WP,WH,true};
    }
    // Brute force 128 sign combos to find no-intersection minimal slope
    auto BuildPtsForMask=[&](int32 Mask, TArray<FVector>& OutPts, TArray<FString>& OutLbls){
        OutPts.Reset(); OutLbls.Reset();
        for(int32 Seg=0; Seg<Anchors.Num(); ++Seg){
            OutPts.Add(Anchors[Seg]); OutLbls.Add(RouteLabels[Seg]);
            bool bPos=(Mask & (1<<Seg))!=0;
            const FOpt& Opt=bPos?BestPos[Seg]:BestNeg[Seg];
            if(Opt.bValid){ OutPts.Add(Opt.Pos); OutLbls.Add(FString::Printf(TEXT("WP_%s_%d"),*RouteLabels[Seg].RightChop(5),Seg)); }
        }
    };
    auto HasIntersect=[&](const TArray<FVector>& Pts)->bool{
        auto OnSeg=[](FVector2D p,FVector2D q,FVector2D r){return q.X<=FMath::Max(p.X,r.X)&&q.X>=FMath::Min(p.X,r.X)&&q.Y<=FMath::Max(p.Y,r.Y)&&q.Y>=FMath::Min(p.Y,r.Y);};
        auto Orient=[](FVector2D p,FVector2D q,FVector2D r){double v=(q.Y-p.Y)*(r.X-q.X)-(q.X-p.X)*(r.Y-q.Y); if(FMath::IsNearlyZero(v,1e-6))return 0; return (v>0)?1:2;};
        auto Inter=[&](FVector2D p1,FVector2D q1,FVector2D p2,FVector2D q2){
            int32 o1=Orient(p1,q1,p2),o2=Orient(p1,q1,q2),o3=Orient(p2,q2,p1),o4=Orient(p2,q2,q1);
            if(o1!=o2&&o3!=o4) return true;
            if(o1==0&&OnSeg(p1,p2,q1))return true; if(o2==0&&OnSeg(p1,q2,q1))return true;
            if(o3==0&&OnSeg(p2,p1,q2))return true; if(o4==0&&OnSeg(p2,q1,q2))return true; return false;
        };
        int32 N=Pts.Num(); for(int32 i=0;i<N;++i){ FVector2D a1(Pts[i].X,Pts[i].Y), b1(Pts[(i+1)%N].X,Pts[(i+1)%N].Y);
            for(int32 j=i+2;j<N;++j){ if(i==0&&j==N-1) continue; FVector2D a2(Pts[j].X,Pts[j].Y), b2(Pts[(j+1)%N].X,Pts[(j+1)%N].Y);
                if(Inter(a1,b1,a2,b2)) return true; }} return false;
    };
    TArray<TArray<FWaypointInfo>> WaypointsPerSeg; WaypointsPerSeg.SetNum(Anchors.Num());
    {
        double BestMaxSlope=1e9, BestLen=1e18; int32 BestMask=-1;
        for(int32 Mask=0; Mask < (1<<Anchors.Num()); ++Mask){
            TArray<FVector> Pts; TArray<FString> Lbls; BuildPtsForMask(Mask,Pts,Lbls);
            if(HasIntersect(Pts)) continue;
            double MaxSlope=0, Tot=0; bool bV=true;
            for(int32 i=0;i<Pts.Num();++i){ double HA=0,HB=0; if(!SampleHeight(Pts[i].X,Pts[i].Y,HA)||!SampleHeight(Pts[(i+1)%Pts.Num()].X,Pts[(i+1)%Pts.Num()].Y,HB)){bV=false;break;}
                double Horiz=FVector2D::Distance(FVector2D(Pts[i].X,Pts[i].Y),FVector2D(Pts[(i+1)%Pts.Num()].X,Pts[(i+1)%Pts.Num()].Y));
                double Slope=(Horiz>1e-6)?FMath::Atan2(FMath::Abs(HB-HA),Horiz)*180.0/PI:0; MaxSlope=FMath::Max(MaxSlope,Slope); Tot+=Horiz; }
            if(!bV) continue; if(MaxSlope>15.0) continue;
            if(MaxSlope<BestMaxSlope-0.01 || (FMath::IsNearlyEqual(MaxSlope,BestMaxSlope,0.1) && Tot<BestLen)){ BestMaxSlope=MaxSlope; BestLen=Tot; BestMask=Mask; }
        }
        if(BestMask==-1){
            BestMaxSlope=1e9;
            for(int32 Mask=0; Mask < (1<<Anchors.Num()); ++Mask){
                TArray<FVector> Pts; TArray<FString> Lbls; BuildPtsForMask(Mask,Pts,Lbls);
                if(HasIntersect(Pts)) continue;
                double MaxSlope=0, Tot=0;
                for(int32 i=0;i<Pts.Num();++i){ double HA=0,HB=0; SampleHeight(Pts[i].X,Pts[i].Y,HA); SampleHeight(Pts[(i+1)%Pts.Num()].X,Pts[(i+1)%Pts.Num()].Y,HB);
                    double Horiz=FVector2D::Distance(FVector2D(Pts[i].X,Pts[i].Y),FVector2D(Pts[(i+1)%Pts.Num()].X,Pts[(i+1)%Pts.Num()].Y));
                    double Slope=(Horiz>1e-6)?FMath::Atan2(FMath::Abs(HB-HA),Horiz)*180.0/PI:0; MaxSlope=FMath::Max(MaxSlope,Slope); Tot+=Horiz; }
                if(MaxSlope<BestMaxSlope-0.01 || (FMath::IsNearlyEqual(MaxSlope,BestMaxSlope,0.1) && Tot<BestLen)){ BestMaxSlope=MaxSlope; BestLen=Tot; BestMask=Mask; }
            }
        }
        if(BestMask!=-1){
            for(int32 Seg=0; Seg<Anchors.Num(); ++Seg){
                bool bPos=(BestMask & (1<<Seg))!=0;
                const FOpt& Opt=bPos?BestPos[Seg]:BestNeg[Seg];
                if(Opt.bValid){
                    const FString WName=FString::Printf(TEXT("WP_%s_%d"),*RouteLabels[Seg].RightChop(5),Seg);
                    WaypointsPerSeg[Seg].Add({Opt.Pos, Opt.Height, WName});
                    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX WAYPOINT %s X=%.1f Y=%.1f TERRAIN_Z=%.1f SEG %s->%s %s"), *WName, Opt.Pos.X, Opt.Pos.Y, Opt.Height, *RouteLabels[Seg], *RouteLabels[(Seg+1)%RouteLabels.Num()], bPos?TEXT("POS"):TEXT("NEG"));
                }
            }
        } else {
            // Fallback to per-segment best without global check
            auto FindBestWaypointFallback = [&](const FVector& A, const FVector& B, FVector& OutWP, double& OutH)->bool{
                double HA=0,HB=0; if(!SampleHeight(A.X,A.Y,HA)||!SampleHeight(B.X,B.Y,HB)) return false;
                const FVector Mid((A.X+B.X)*0.5,(A.Y+B.Y)*0.5,0);
                const FVector Dir(B.X-A.X,B.Y-A.Y,0);
                const double Len=FVector2D::Distance(FVector2D(A.X,A.Y),FVector2D(B.X,B.Y)); if(Len<1e-6) return false;
                const FVector Perp(-Dir.Y/Len, Dir.X/Len,0);
                const TArray<double> Offs={ -40000,-30000,-20000,-15000,-10000,10000,15000,20000,30000,40000,-50000,50000};
                double BestSlope=1e9,BestLen=1e9; bool bFound=false; FVector BestWP; double BestHW=0;
                for(double Off:Offs){ const double X=Mid.X+Perp.X*Off, Y=Mid.Y+Perp.Y*Off; if(X<0||X>409600||Y<0||Y>409600) continue; double HW=0; if(!SampleHeight(X,Y,HW)) continue;
                    const double d1=FVector2D::Distance(FVector2D(A.X,A.Y),FVector2D(X,Y)), d2=FVector2D::Distance(FVector2D(X,Y),FVector2D(B.X,B.Y));
                    if(d1<1e-6||d2<1e-6) continue; const double s1=FMath::Atan2(FMath::Abs(HW-HA),d1)*180.0/PI, s2=FMath::Atan2(FMath::Abs(HB-HW),d2)*180.0/PI; const double MaxSlope=FMath::Max(s1,s2); const double Tot=d1+d2;
                    if(MaxSlope<BestSlope-0.01 || (FMath::IsNearlyEqual(MaxSlope,BestSlope,0.1) && Tot<BestLen)){BestSlope=MaxSlope;BestLen=Tot;BestWP=FVector(X,Y,HW);BestHW=HW;bFound=true;}}
                if(!bFound) return false; OutWP=BestWP; OutH=BestHW; return true;
            };
            for(int32 Seg=0; Seg<Anchors.Num(); ++Seg){
                FVector WP; double WH;
                if(FindBestWaypointFallback(Anchors[Seg], Anchors[(Seg+1)%Anchors.Num()], WP, WH)){
                    const FString WName=FString::Printf(TEXT("WP_%s_%d"),*RouteLabels[Seg].RightChop(5),Seg);
                    WaypointsPerSeg[Seg].Add({WP,WH,WName});
                }
            }
        }
    }

    // Build expanded anchor list
    TArray<FVector> ExpandedAnchors;
    TArray<FString> ExpandedLabels;
    for (int32 Seg=0; Seg<Anchors.Num(); ++Seg)
    {
        ExpandedAnchors.Add(Anchors[Seg]); ExpandedLabels.Add(RouteLabels[Seg]);
        for (auto& W : WaypointsPerSeg[Seg]) { ExpandedAnchors.Add(W.Pos); ExpandedLabels.Add(W.Name); }
    }

    // Now destroy old guide
    for (AActor* A : ExistingTour)
    {
        A->Destroy();
    }

    TArray<double> ExpandedHeights;
    for (const FVector& EA : ExpandedAnchors)
    {
        double Hz=0;
        SampleHeight(EA.X, EA.Y, Hz);
        ExpandedHeights.Add(Hz);
    }

    // Create spline from expanded anchors (smooth Curve)
    AActor* GuideActor = World->SpawnActor<AActor>(AActor::StaticClass(), FTransform::Identity);
    if (!GuideActor)
    {
        UE_LOG(LogTemp, Error, TEXT("FixTourRoad failed: could not spawn guide actor."));
        return false;
    }
    GuideActor->SetActorLabel(TEXT("TOUR_RoadGuide"));
    GuideActor->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide")));
    USceneComponent* Root = NewObject<USceneComponent>(GuideActor, TEXT("Root"));
    Root->RegisterComponent();
    GuideActor->SetRootComponent(Root);
    GuideActor->AddInstanceComponent(Root);
    USplineComponent* Spline = NewObject<USplineComponent>(GuideActor, TEXT("TourSpline"));
    Spline->SetupAttachment(Root);
    Spline->SetClosedLoop(true);
    Spline->ClearSplinePoints(false);
    for (int32 i = 0; i < ExpandedAnchors.Num(); ++i)
    {
        const FVector CP(ExpandedAnchors[i].X, ExpandedAnchors[i].Y, ExpandedHeights[i] + 80.0);
        Spline->AddSplinePoint(CP, ESplineCoordinateSpace::World, false);
        Spline->SetSplinePointType(i, ESplinePointType::Curve, false);
    }
    Spline->UpdateSpline();
    Spline->RegisterComponent();
    GuideActor->AddInstanceComponent(Spline);

    // Sample the smooth spline at regular intervals, then snap each sample to actual terrain height
    constexpr double SplineStepCm = 2000.0;
    constexpr double HeightOffsetCm = 80.0;
    const double SplineLen = Spline->GetSplineLength();
    TArray<FVector> Sampled;
    Sampled.Reserve(512);
    double TotalLengthCm = 0.0;
    int32 NoHitCount = 0;
    const int32 NumSteps = FMath::Max(1, FMath::CeilToInt(SplineLen / SplineStepCm));
    for (int32 s = 0; s <= NumSteps; ++s)
    {
        const double Dist = (SplineLen * s) / NumSteps;
        const FVector SplinePos = Spline->GetLocationAtDistanceAlongSpline(Dist, ESplineCoordinateSpace::World);
        double Hz = 0;
        if (!SampleHeight(SplinePos.X, SplinePos.Y, Hz)) { ++NoHitCount; continue; }
        const FVector P(SplinePos.X, SplinePos.Y, Hz + HeightOffsetCm);
        if (Sampled.Num() > 0) TotalLengthCm += FVector::Dist(Sampled.Last(), P);
        Sampled.Add(P);
    }

    // Per-control-point slope and bend analysis
    bool bAnyOver15 = false;
    double MaxSlopeOverall = 0.0;
    for (int32 Seg = 0; Seg < ExpandedAnchors.Num(); ++Seg)
    {
        const double HA = ExpandedHeights[Seg];
        const double HB = ExpandedHeights[(Seg + 1) % ExpandedHeights.Num()];
        const double Horiz = FVector2D::Distance(FVector2D(ExpandedAnchors[Seg].X, ExpandedAnchors[Seg].Y), FVector2D(ExpandedAnchors[(Seg + 1) % ExpandedAnchors.Num()].X, ExpandedAnchors[(Seg + 1) % ExpandedAnchors.Num()].Y));
        const double SlopeDeg = (Horiz > 1e-6) ? FMath::Atan2(FMath::Abs(HB - HA), Horiz) * 180.0 / PI : 0.0;
        MaxSlopeOverall = FMath::Max(MaxSlopeOverall, SlopeDeg);
        if (SlopeDeg > 15.0) bAnyOver15 = true;
        UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX SEG %d: %s -> %s HORIZ=%.0f DELTA_Z=%.0f SLOPE=%.1f deg%s"),
            Seg, *ExpandedLabels[Seg], *ExpandedLabels[(Seg+1)%ExpandedLabels.Num()], Horiz, HB - HA, SlopeDeg, SlopeDeg > 15.0 ? TEXT(" STILL_EXTREME") : TEXT(""));
    }
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX TOTAL_LENGTH=%.1f cm (%.3f km) POINTS=%d NO_HIT=%d WAYPOINTS_ADDED=%d"), TotalLengthCm, TotalLengthCm/100000.0, Sampled.Num(), NoHitCount, [&](){int32 C=0; for(auto& A:WaypointsPerSeg) C+=A.Num(); return C;}());
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX ANY_OVER_15=%s"), bAnyOver15 ? TEXT("YES") : TEXT("NO"));
    double MaxTurnDeg = 0.0;
    double MinBendRadiusCm = 1e12;
    for (int32 i = 1; i < ExpandedAnchors.Num()-1; ++i)
    {
        const FVector v1 = ExpandedAnchors[i] - ExpandedAnchors[i-1];
        const FVector v2 = ExpandedAnchors[i+1] - ExpandedAnchors[i];
        const double l1 = FVector2D::Distance(FVector2D(ExpandedAnchors[i-1].X, ExpandedAnchors[i-1].Y), FVector2D(ExpandedAnchors[i].X, ExpandedAnchors[i].Y));
        const double l2 = FVector2D::Distance(FVector2D(ExpandedAnchors[i].X, ExpandedAnchors[i].Y), FVector2D(ExpandedAnchors[i+1].X, ExpandedAnchors[i+1].Y));
        if (l1 < 1e-6 || l2 < 1e-6) continue;
        const double dot = (v1.X*v2.X + v1.Y*v2.Y) / (l1*l2);
        const double ang = FMath::Acos(FMath::Clamp(dot, -1.0, 1.0)) * 180.0 / PI;
        MaxTurnDeg = FMath::Max(MaxTurnDeg, ang);
        if (ang > 1.0)
        {
            const double avgLen = (l1 + l2) * 0.5;
            const double rad = avgLen / (2.0 * FMath::Sin(ang * PI / 360.0));
            MinBendRadiusCm = FMath::Min(MinBendRadiusCm, rad);
        }
    }
    {
        const int32 n = ExpandedAnchors.Num();
        const FVector v1 = ExpandedAnchors[0] - ExpandedAnchors[n-1];
        const FVector v2 = ExpandedAnchors[1] - ExpandedAnchors[0];
        const double l1 = FVector2D::Distance(FVector2D(ExpandedAnchors[n-1].X, ExpandedAnchors[n-1].Y), FVector2D(ExpandedAnchors[0].X, ExpandedAnchors[0].Y));
        const double l2 = FVector2D::Distance(FVector2D(ExpandedAnchors[0].X, ExpandedAnchors[0].Y), FVector2D(ExpandedAnchors[1].X, ExpandedAnchors[1].Y));
        if (l1 > 1e-6 && l2 > 1e-6)
        {
            const double dot = (v1.X*v2.X + v1.Y*v2.Y) / (l1*l2);
            const double ang = FMath::Acos(FMath::Clamp(dot, -1.0, 1.0)) * 180.0 / PI;
            MaxTurnDeg = FMath::Max(MaxTurnDeg, ang);
            if (ang > 1.0)
            {
                const double avgLen = (l1 + l2) * 0.5;
                const double rad = avgLen / (2.0 * FMath::Sin(ang * PI / 360.0));
                MinBendRadiusCm = FMath::Min(MinBendRadiusCm, rad);
            }
        }
    }
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX CONTROL_POINTS=%d MAX_SLOPE=%.1f deg MAX_TURN=%.1f deg MIN_BEND_RADIUS=%.0f cm (%.1f m)"),
        ExpandedAnchors.Num(), MaxSlopeOverall, MaxTurnDeg, MinBendRadiusCm < 1e11 ? MinBendRadiusCm : -1, MinBendRadiusCm < 1e11 ? MinBendRadiusCm/100.0 : -1);

    // Self-intersection check
    {
        auto OnSeg2=[](FVector2D p,FVector2D q,FVector2D r){return q.X<=FMath::Max(p.X,r.X)&&q.X>=FMath::Min(p.X,r.X)&&q.Y<=FMath::Max(p.Y,r.Y)&&q.Y>=FMath::Min(p.Y,r.Y);};
        auto Orient2=[](FVector2D p,FVector2D q,FVector2D r){double v=(q.Y-p.Y)*(r.X-q.X)-(q.X-p.X)*(r.Y-q.Y); if(FMath::IsNearlyZero(v,1e-6))return 0; return (v>0)?1:2;};
        auto Inter2=[&](FVector2D p1,FVector2D q1,FVector2D p2,FVector2D q2){
            int32 o1=Orient2(p1,q1,p2),o2=Orient2(p1,q1,q2),o3=Orient2(p2,q2,p1),o4=Orient2(p2,q2,q1);
            if(o1!=o2&&o3!=o4) return true;
            if(o1==0&&OnSeg2(p1,p2,q1))return true; if(o2==0&&OnSeg2(p1,q2,q1))return true;
            if(o3==0&&OnSeg2(p2,p1,q2))return true; if(o4==0&&OnSeg2(p2,q1,q2))return true; return false;
        };
        bool bSelf=false; int32 N=ExpandedAnchors.Num();
        for(int32 i=0;i<N && !bSelf;++i){ FVector2D a1(ExpandedAnchors[i].X,ExpandedAnchors[i].Y), b1(ExpandedAnchors[(i+1)%N].X,ExpandedAnchors[(i+1)%N].Y);
            for(int32 j=i+2;j<N;++j){ if(i==0&&j==N-1) continue; FVector2D a2(ExpandedAnchors[j].X,ExpandedAnchors[j].Y), b2(ExpandedAnchors[(j+1)%N].X,ExpandedAnchors[(j+1)%N].Y);
                if(Inter2(a1,b1,a2,b2)){ bSelf=true; break; }}}
        UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX SELF_INTERSECT=%s"), bSelf?TEXT("YES"):TEXT("NO"));
        for (const FString& Lbl : RouteLabels)
        {
            AActor** F = JP93Map.Find(Lbl);
            if (!F) continue;
            const FVector Loc=(*F)->GetActorLocation();
            double MinDist=1e18;
            for(int32 k=0;k<ExpandedAnchors.Num();++k){ double d=FVector2D::Distance(FVector2D(Loc.X,Loc.Y),FVector2D(ExpandedAnchors[k].X,ExpandedAnchors[k].Y)); MinDist=FMath::Min(MinDist,d); }
            // Also check distance to spline-sampled points
            for(auto& P: Sampled){ double d=FVector2D::Distance(FVector2D(Loc.X,Loc.Y),FVector2D(P.X,P.Y)); MinDist=FMath::Min(MinDist,d); }
            UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX CLOSEST %s = %.0f cm %s"), *Lbl, MinDist, MinDist>15000?TEXT("FAR>150m"):TEXT(""));
        }
    }

    // Reuse the spline's sampled points for segment spheres (already terrain-snapped)
    UObject* SphereMesh = StaticLoadObject(UStaticMesh::StaticClass(), nullptr, TEXT("/Engine/BasicShapes/Sphere"));
    UMaterial* RoadMat = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
    if (!RoadMat) RoadMat = LoadObject<UMaterial>(nullptr, TEXT("/Engine/EngineMaterials/WorldGridMaterial"));
    int32 SphereCount = 0;
    for (int32 i = 0; i < Sampled.Num(); i += 3)
    {
        AActor* Seg = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator::ZeroRotator, Sampled[i]));
        if (!Seg) continue;
        if (UStaticMeshComponent* SMC = Cast<AStaticMeshActor>(Seg)->GetStaticMeshComponent())
        {
            SMC->SetStaticMesh(Cast<UStaticMesh>(SphereMesh));
            SMC->SetWorldScale3D(FVector(0.9f));
            if (RoadMat) SMC->SetMaterial(0, RoadMat);
        }
        Seg->SetActorLabel(FString::Printf(TEXT("TOUR_Seg_%03d"), SphereCount));
        Seg->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide/Segments")));
        ++SphereCount;
    }
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FIX SPHERES=%d SPLINE_POINTS=%d"), SphereCount, Sampled.Num());

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("FixTourRoad failed: could not save level."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JURASSIC PARK TOUR ROAD GUIDE FIXED: %.3f km, %d waypoints added."), TotalLengthCm/100000.0, [&](){int32 C=0; for(auto& A:WaypointsPerSeg) C+=A.Num(); return C;}());
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::EnhanceTourRoadVisualization()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("EnhanceTourRoadVisualization refused: editor is unavailable."));
        return false;
    }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("EnhanceTourRoadVisualization refused: target map is not active."));
        return false;
    }
    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    AActor* GuideActor = nullptr;
    USplineComponent* Spline = nullptr;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It))
        {
            ++LandscapeCount;
            Landscape = Proxy;
        }
        if (It->GetActorLabel() == TEXT("TOUR_RoadGuide"))
        {
            GuideActor = *It;
            Spline = GuideActor->FindComponentByClass<USplineComponent>();
        }
    }
    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("EnhanceTourRoadVisualization refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
        return false;
    }
    if (!GuideActor || !Spline)
    {
        UE_LOG(LogTemp, Error, TEXT("EnhanceTourRoadVisualization refused: TOUR_RoadGuide spline not found."));
        return false;
    }
    const int32 OrigSplinePoints = Spline->GetNumberOfSplinePoints();
    const double OrigSplineLen = Spline->GetSplineLength();
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_VIS CONFIRM SPLINE_POINTS=%d LENGTH=%.1f cm (%.3f km) UNCHANGED"), OrigSplinePoints, OrigSplineLen, OrigSplineLen/100000.0);

    // Remove old sparse TOUR_Seg_* spheres (keep guide)
    TArray<AActor*> OldSegs;
    for (FActorIterator It(World); It; ++It)
    {
        const FString L = It->GetActorLabel();
        if (L.StartsWith(TEXT("TOUR_Seg_")))
        {
            OldSegs.Add(*It);
        }
    }
    int32 Removed = 0;
    for (AActor* A : OldSegs) { A->Destroy(); ++Removed; }
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_VIS REMOVED_SPARSE_SEGMENTS=%d"), Removed);

    // Prepare dense continuous ribbon: sample spline densely, snap to terrain +200cm, create overlapping planes
    auto SampleHeightVis = [&](double X, double Y, double& OutZ) -> bool
    {
        const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
        if (!H.IsSet()) return false;
        OutZ = static_cast<double>(H.GetValue());
        return true;
    };

    // Ensure ribbon material exists (bright emissive ~10m wide)
    const FString RibbonMatPath = TEXT("/Game/Temp/TourRoad/MK_TourRibbon");
    UMaterial* RibbonMat = LoadObject<UMaterial>(nullptr, *RibbonMatPath);
    if (!RibbonMat)
    {
        // Try to reuse existing marker material as fallback, will still be visible
        RibbonMat = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
        if (!RibbonMat) RibbonMat = LoadObject<UMaterial>(nullptr, TEXT("/Engine/EngineMaterials/WorldGridMaterial"));
        UE_LOG(LogTemp, Display, TEXT("JPTOUR_VIS RIBBON_MAT_FALLBACK=%s"), RibbonMat ? *RibbonMat->GetName() : TEXT("NONE"));
    }
    else
    {
        UE_LOG(LogTemp, Display, TEXT("JPTOUR_VIS RIBBON_MAT=%s"), *RibbonMatPath);
    }

    UObject* PlaneMesh = StaticLoadObject(UStaticMesh::StaticClass(), nullptr, TEXT("/Engine/BasicShapes/Plane"));
    if (!PlaneMesh)
    {
        UE_LOG(LogTemp, Error, TEXT("EnhanceTourRoadVisualization failed: missing Plane mesh."));
        return false;
    }

    constexpr double TargetWidthCm = 1000.0; // 10m wide
    constexpr double HeightOffsetCm = 200.0; // 150-250cm range
    constexpr double StepCm = 800.0; // dense enough for continuous appearance from top view
    const double SplineLenVis = Spline->GetSplineLength();
    const int32 NumSteps = FMath::Max(1, FMath::CeilToInt(SplineLenVis / StepCm));
    TArray<FVector> RibbonPoints;
    RibbonPoints.Reserve(NumSteps + 1);
    for (int32 s = 0; s <= NumSteps; ++s)
    {
        const double Dist = (SplineLenVis * s) / NumSteps;
        const FVector SPos = Spline->GetLocationAtDistanceAlongSpline(Dist, ESplineCoordinateSpace::World);
        double Hz = 0;
        if (!SampleHeightVis(SPos.X, SPos.Y, Hz)) continue;
        RibbonPoints.Add(FVector(SPos.X, SPos.Y, Hz + HeightOffsetCm));
    }

    int32 RibbonSegments = 0;
    for (int32 i = 0; i < RibbonPoints.Num(); ++i)
    {
        const FVector& P0 = RibbonPoints[i];
        const FVector& P1 = RibbonPoints[(i + 1) % RibbonPoints.Num()];
        const double SegLen = FVector::Dist(P0, P1);
        if (SegLen < 1e-3) continue;
        const FVector Mid = (P0 + P1) * 0.5;
        const double Yaw = FMath::Atan2(P1.Y - P0.Y, P1.X - P0.X) * 180.0 / PI;
        // Add 10% overlap to hide seams
        const double LenWithOverlap = SegLen * 1.08;
        AActor* SegActor = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator(0.0, Yaw, 0.0), Mid));
        if (!SegActor) continue;
        if (UStaticMeshComponent* SMC = Cast<AStaticMeshActor>(SegActor)->GetStaticMeshComponent())
        {
            SMC->SetStaticMesh(Cast<UStaticMesh>(PlaneMesh));
            // Plane is 100x100, scale X = length/100, Y = width/100
            SMC->SetWorldScale3D(FVector(LenWithOverlap / 100.0, TargetWidthCm / 100.0, 1.0));
            if (RibbonMat) SMC->SetMaterial(0, RibbonMat);
            SMC->SetMobility(EComponentMobility::Movable);
            SMC->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            SMC->SetCastShadow(false);
        }
        SegActor->SetActorLabel(FString::Printf(TEXT("TOUR_Ribbon_%04d"), RibbonSegments));
        SegActor->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide/Visualization")));
        ++RibbonSegments;
    }

    UE_LOG(LogTemp, Display, TEXT("JPTOUR_VIS RIBBON_SEGMENTS=%d WIDTH=%.0f cm HEIGHT_OFFSET=%.0f cm STEP=%.0f cm"), RibbonSegments, TargetWidthCm, HeightOffsetCm, StepCm);
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_VIS SPLINE_UNCHANGED_POINTS=%d"), OrigSplinePoints);

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("EnhanceTourRoadVisualization failed: could not save level."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JURASSIC PARK TOUR ROAD VISUAL ENHANCED: %d ribbon segments."), RibbonSegments);
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::FixTourRoadCusps()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps refused: editor is unavailable."));
        return false;
    }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps refused: target map is not active."));
        return false;
    }
    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    AActor* GuideActor = nullptr;
    USplineComponent* Spline = nullptr;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It))
        {
            ++LandscapeCount;
            Landscape = Proxy;
        }
        if (It->GetActorLabel() == TEXT("TOUR_RoadGuide"))
        {
            GuideActor = *It;
            Spline = GuideActor->FindComponentByClass<USplineComponent>();
        }
        if (It->GetActorLabel().StartsWith(TEXT("JP93_")))
        {
            // ensure JP93 markers exist but do not move them
        }
    }
    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
        return false;
    }
    if (!GuideActor || !Spline)
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps refused: TOUR_RoadGuide spline not found."));
        return false;
    }
    const int32 NumPoints = Spline->GetNumberOfSplinePoints();
    if (NumPoints < 6)
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps refused: spline has too few points (%d)."), NumPoints);
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JPCUSP ORIGINAL_POINTS=%d LENGTH=%.1f cm (%.3f km)"), NumPoints, Spline->GetSplineLength(), Spline->GetSplineLength()/100000.0);

    auto SampleHeightCusp = [&](double X, double Y, double& OutZ) -> bool
    {
        const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
        if (!H.IsSet()) return false;
        OutZ = static_cast<double>(H.GetValue());
        return true;
    };

    struct FCuspInfo { int32 Index; double AngleDeg; double RadiusCm; FVector Pos; double MaxSlopeDeg; bool bIsWaypoint; };
    TArray<FCuspInfo> AllCusps;
    for (int32 i = 0; i < NumPoints; ++i)
    {
        const FVector Prev = Spline->GetLocationAtSplinePoint((i - 1 + NumPoints) % NumPoints, ESplineCoordinateSpace::World);
        const FVector Curr = Spline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World);
        const FVector Next = Spline->GetLocationAtSplinePoint((i + 1) % NumPoints, ESplineCoordinateSpace::World);
        const FVector v1 = Curr - Prev;
        const FVector v2 = Next - Curr;
        const double l1 = FVector2D::Distance(FVector2D(Prev.X, Prev.Y), FVector2D(Curr.X, Curr.Y));
        const double l2 = FVector2D::Distance(FVector2D(Curr.X, Curr.Y), FVector2D(Next.X, Next.Y));
        if (l1 < 1e-6 || l2 < 1e-6) continue;
        const double dot = (v1.X * v2.X + v1.Y * v2.Y) / (l1 * l2);
        const double ang = FMath::Acos(FMath::Clamp(dot, -1.0, 1.0)) * 180.0 / PI;
        double rad = 1e12;
        if (ang > 1.0)
        {
            const double avgLen = (l1 + l2) * 0.5;
            rad = avgLen / (2.0 * FMath::Sin(ang * PI / 360.0));
        }
        double HPrev=0, HCurr=0, HNext=0;
        SampleHeightCusp(Prev.X, Prev.Y, HPrev); SampleHeightCusp(Curr.X, Curr.Y, HCurr); SampleHeightCusp(Next.X, Next.Y, HNext);
        const double s1 = (l1>1e-6)?FMath::Atan2(FMath::Abs(HCurr-HPrev), l1)*180.0/PI:0;
        const double s2 = (l2>1e-6)?FMath::Atan2(FMath::Abs(HNext-HCurr), l2)*180.0/PI:0;
        const double maxSlope = FMath::Max(s1,s2);
        const bool bIsWP = (i % 2 == 1); // waypoints are odd in our 14-point loop
        AllCusps.Add({ i, ang, rad, Curr, maxSlope, bIsWP });
        UE_LOG(LogTemp, Display, TEXT("JPCUSP %s %d ANGLE=%.1f deg RADIUS=%.0f cm SLOPE=%.1f deg POS=%.0f,%.0f"), bIsWP?TEXT("WAYPOINT"):TEXT("ANCHOR"), i, ang, rad, maxSlope, Curr.X, Curr.Y);
    }
    // Sort descending by angle (sharpest first), but prioritize waypoints slightly
    TArray<FCuspInfo> WaypointCusps;
    for (auto& C : AllCusps) if (C.bIsWaypoint) WaypointCusps.Add(C);
    // Include anchors as candidates for fixing via neighboring waypoints
    TArray<FCuspInfo> AnchorCusps;
    for (auto& C : AllCusps) if (!C.bIsWaypoint) AnchorCusps.Add(C);
    WaypointCusps.Sort([](const FCuspInfo& A, const FCuspInfo& B){
        if (!FMath::IsNearlyEqual(A.MaxSlopeDeg, B.MaxSlopeDeg, 0.1)) return A.MaxSlopeDeg > B.MaxSlopeDeg;
        return A.AngleDeg > B.AngleDeg;
    });
    AnchorCusps.Sort([](const FCuspInfo& A, const FCuspInfo& B){ return A.AngleDeg > B.AngleDeg; });
    if (WaypointCusps.Num() < 2)
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps refused: not enough waypoints to fix."));
        return false;
    }
    // User requested: smooth only upper-middle and lower-middle cusps (Brach->Gallim and Gallim->Triceratops waypoints)
    // These are at indices 5 and 7 in the 14-point loop
    TArray<FCuspInfo> ToFix;
    for (int32 wantIdx : {5, 7})
    {
        for (auto& C : WaypointCusps) if (C.Index == wantIdx) { ToFix.Add(C); break; }
    }
    // Fallback to sharpest if not found
    if (ToFix.Num() < 2)
    {
        for (auto& C : WaypointCusps)
        {
            bool bAlready = false; for (auto& F : ToFix) if (F.Index == C.Index) bAlready = true;
            if (!bAlready) ToFix.Add(C);
            if (ToFix.Num() == 2) break;
        }
    }
    UE_LOG(LogTemp, Display, TEXT("JPCUSP SELECTED %d and %d for smoothing (%.1f deg, %.1f deg)"), ToFix[0].Index, ToFix[1].Index, ToFix[0].AngleDeg, ToFix[1].AngleDeg);

    struct FFixRecord { int32 Index; FVector OldPos; FVector NewPos; double OldAngle; double NewAngle; double OldSlope0; double OldSlope1; double NewSlope0; double NewSlope1; };
    TArray<FFixRecord> Fixes;

    for (auto& Cusp : ToFix)
    {
        const int32 idx = Cusp.Index;
        const int32 prevIdx = (idx - 1 + NumPoints) % NumPoints;
        const int32 nextIdx = (idx + 1) % NumPoints;
        const FVector PrevPos = Spline->GetLocationAtSplinePoint(prevIdx, ESplineCoordinateSpace::World);
        const FVector NextPos = Spline->GetLocationAtSplinePoint(nextIdx, ESplineCoordinateSpace::World);
        const FVector OldPos = Spline->GetLocationAtSplinePoint(idx, ESplineCoordinateSpace::World);
        // New position: search along perpendicular bisector for valley-low and smooth turn
        const double MidX0 = (PrevPos.X + NextPos.X) * 0.5;
        const double MidY0 = (PrevPos.Y + NextPos.Y) * 0.5;
        const FVector Mid0(MidX0, MidY0, 0);
        const FVector DirN(NextPos.X - PrevPos.X, NextPos.Y - PrevPos.Y, 0);
        const double LenN = FVector2D::Distance(FVector2D(PrevPos.X, PrevPos.Y), FVector2D(NextPos.X, NextPos.Y));
        const FVector PerpN = LenN > 1e-6 ? FVector(-DirN.Y / LenN, DirN.X / LenN, 0) : FVector(0,1,0);
        double BestNewX = OldPos.X, BestNewY = OldPos.Y;
        double BestScore = 1e18;
        double BestNewHz = 0; SampleHeightCusp(OldPos.X, OldPos.Y, BestNewHz);
        // Search offsets along perp from midpoint, from -40k to +40k
        for (double Off = -40000; Off <= 40000; Off += 5000)
        {
            const double X = MidX0 + PerpN.X * Off;
            const double Y = MidY0 + PerpN.Y * Off;
            if (X < 0 || X > 409600 || Y < 0 || Y > 409600) continue;
            double Hz = 0; if (!SampleHeightCusp(X, Y, Hz)) continue;
            const double d1 = FVector2D::Distance(FVector2D(PrevPos.X, PrevPos.Y), FVector2D(X, Y));
            const double d2 = FVector2D::Distance(FVector2D(X, Y), FVector2D(NextPos.X, NextPos.Y));
            if (d1 < 1e-6 || d2 < 1e-6) continue;
            double HPrev2=0, HNext2=0; SampleHeightCusp(PrevPos.X, PrevPos.Y, HPrev2); SampleHeightCusp(NextPos.X, NextPos.Y, HNext2);
            const double s1 = FMath::Atan2(FMath::Abs(Hz - HPrev2), d1) * 180.0 / PI;
            const double s2 = FMath::Atan2(FMath::Abs(HNext2 - Hz), d2) * 180.0 / PI;
            const double MaxSlope = FMath::Max(s1, s2);
            const FVector v1(X - PrevPos.X, Y - PrevPos.Y, 0), v2(NextPos.X - X, NextPos.Y - Y, 0);
            const double l1 = d1, l2 = d2;
            const double dot = (v1.X*v2.X + v1.Y*v2.Y) / (l1*l2);
            const double ang = FMath::Acos(FMath::Clamp(dot, -1.0, 1.0)) * 180.0 / PI;
            double Score = MaxSlope * 1000.0 + ang * 10.0;
            if (MaxSlope > 15.0) Score += 50000;
            if (MaxSlope > 10.0) Score += 10000;
            if (ang > 90.0) Score += 20000;
            // Prefer lower height (valley)
            Score += Hz * 0.01;
            if (Score < BestScore)
            {
                BestScore = Score;
                BestNewX = X; BestNewY = Y; BestNewHz = Hz;
            }
        }
        const double NewX = BestNewX;
        const double NewY = BestNewY;
        double NewHz = BestNewHz;
        if (!SampleHeightCusp(NewX, NewY, NewHz))
        {
            UE_LOG(LogTemp, Warning, TEXT("JPCUSP skip %d: no terrain height at smoothed XY."), idx);
            continue;
        }
        const FVector NewPos(NewX, NewY, NewHz + 80.0);
        // Compute old slopes
        double HPrev=0, HOld=0, HNext=0, HNew=0;
        SampleHeightCusp(PrevPos.X, PrevPos.Y, HPrev);
        SampleHeightCusp(OldPos.X, OldPos.Y, HOld);
        SampleHeightCusp(NextPos.X, NextPos.Y, HNext);
        SampleHeightCusp(NewX, NewY, HNew);
        const double dPrevOld = FVector2D::Distance(FVector2D(PrevPos.X, PrevPos.Y), FVector2D(OldPos.X, OldPos.Y));
        const double dOldNext = FVector2D::Distance(FVector2D(OldPos.X, OldPos.Y), FVector2D(NextPos.X, NextPos.Y));
        const double dPrevNew = FVector2D::Distance(FVector2D(PrevPos.X, PrevPos.Y), FVector2D(NewX, NewY));
        const double dNewNext = FVector2D::Distance(FVector2D(NewX, NewY), FVector2D(NextPos.X, NextPos.Y));
        const double oldS0 = (dPrevOld>1e-6)?FMath::Atan2(FMath::Abs(HOld-HPrev), dPrevOld)*180.0/PI:0;
        const double oldS1 = (dOldNext>1e-6)?FMath::Atan2(FMath::Abs(HNext-HOld), dOldNext)*180.0/PI:0;
        const double newS0 = (dPrevNew>1e-6)?FMath::Atan2(FMath::Abs(HNew-HPrev), dPrevNew)*180.0/PI:0;
        const double newS1 = (dNewNext>1e-6)?FMath::Atan2(FMath::Abs(HNext-HNew), dNewNext)*180.0/PI:0;
        // Compute new angle after fix
        const FVector v1New = NewPos - PrevPos;
        const FVector v2New = NextPos - NewPos;
        const double l1n = FVector2D::Distance(FVector2D(PrevPos.X, PrevPos.Y), FVector2D(NewX, NewY));
        const double l2n = FVector2D::Distance(FVector2D(NewX, NewY), FVector2D(NextPos.X, NextPos.Y));
        double newAng = Cusp.AngleDeg;
        if (l1n > 1e-6 && l2n > 1e-6)
        {
            const double dotN = (v1New.X*v2New.X + v1New.Y*v2New.Y) / (l1n*l2n);
            newAng = FMath::Acos(FMath::Clamp(dotN, -1.0, 1.0)) * 180.0 / PI;
        }
        Spline->SetLocationAtSplinePoint(idx, NewPos, ESplineCoordinateSpace::World, false);
        Fixes.Add({ idx, OldPos, NewPos, Cusp.AngleDeg, newAng, oldS0, oldS1, newS0, newS1 });
        UE_LOG(LogTemp, Display, TEXT("JPCUSP FIXED %d: OLD(%.0f,%.0f) angle=%.1f slopes %.1f/%.1f -> NEW(%.0f,%.0f) angle=%.1f slopes %.1f/%.1f"), idx, OldPos.X, OldPos.Y, Cusp.AngleDeg, oldS0, oldS1, NewX, NewY, newAng, newS0, newS1);
        if (newS0 > 15.0 || newS1 > 15.0)
        {
            UE_LOG(LogTemp, Warning, TEXT("JPCUSP WARNING: fixed segment still >15 deg"));
        }
    }

    Spline->UpdateSpline();

    // Verify zero XY self-intersections on updated spline control polygon
    {
        TArray<FVector> Pts;
        for (int32 i = 0; i < Spline->GetNumberOfSplinePoints(); ++i) Pts.Add(Spline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World));
        auto OnSeg=[&](FVector2D p,FVector2D q,FVector2D r){return q.X<=FMath::Max(p.X,r.X)&&q.X>=FMath::Min(p.X,r.X)&&q.Y<=FMath::Max(p.Y,r.Y)&&q.Y>=FMath::Min(p.Y,r.Y);};
        auto Orient=[&](FVector2D p,FVector2D q,FVector2D r){double v=(q.Y-p.Y)*(r.X-q.X)-(q.X-p.X)*(r.Y-q.Y); if(FMath::IsNearlyZero(v,1e-6))return 0; return (v>0)?1:2;};
        auto Inter=[&](FVector2D p1,FVector2D q1,FVector2D p2,FVector2D q2){
            int32 o1=Orient(p1,q1,p2),o2=Orient(p1,q1,q2),o3=Orient(p2,q2,p1),o4=Orient(p2,q2,q1);
            if(o1!=o2&&o3!=o4) return true;
            if(o1==0&&OnSeg(p1,p2,q1))return true; if(o2==0&&OnSeg(p1,q2,q1))return true;
            if(o3==0&&OnSeg(p2,p1,q2))return true; if(o4==0&&OnSeg(p2,q1,q2))return true; return false;
        };
        bool bSelf=false; int32 N=Pts.Num();
        for(int32 i=0;i<N && !bSelf;++i){ FVector2D a1(Pts[i].X,Pts[i].Y), b1(Pts[(i+1)%N].X,Pts[(i+1)%N].Y);
            for(int32 j=i+2;j<N;++j){ if(i==0&&j==N-1) continue; FVector2D a2(Pts[j].X,Pts[j].Y), b2(Pts[(j+1)%N].X,Pts[(j+1)%N].Y);
                if(Inter(a1,b1,a2,b2)){ bSelf=true; break; }}}
        UE_LOG(LogTemp, Display, TEXT("JPCUSP SELF_INTERSECT=%s"), bSelf?TEXT("YES"):TEXT("NO"));
        if (bSelf)
        {
            UE_LOG(LogTemp, Error, TEXT("FixCusps failed: still self-intersecting after fix."));
            return false;
        }
    }

    // Report overall metrics after fix
    {
        double MaxSlope=0, MaxTurn=0, MinBendRadiusCm=1e12, TotalLen=0;
        int32 N=Spline->GetNumberOfSplinePoints();
        for(int32 i=0;i<N;++i){
            const FVector A=Spline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World);
            const FVector B=Spline->GetLocationAtSplinePoint((i+1)%N, ESplineCoordinateSpace::World);
            const TOptional<float> HAOpt = Landscape->GetHeightAtLocation(FVector(A.X, A.Y, 0.0));
            const TOptional<float> HBOpt = Landscape->GetHeightAtLocation(FVector(B.X, B.Y, 0.0));
            if (!HAOpt.IsSet() || !HBOpt.IsSet()) continue;
            const double HA = HAOpt.GetValue(); const double HB = HBOpt.GetValue();
            double Horiz=FVector2D::Distance(FVector2D(A.X,A.Y),FVector2D(B.X,B.Y));
            double Slope=(Horiz>1e-6)?FMath::Atan2(FMath::Abs(HB-HA),Horiz)*180.0/PI:0;
            MaxSlope=FMath::Max(MaxSlope,Slope);
            TotalLen+=FVector::Dist(A,B);
        }
        for(int32 i=1;i<N-1;++i){
            const FVector Prev=Spline->GetLocationAtSplinePoint(i-1, ESplineCoordinateSpace::World);
            const FVector Curr=Spline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World);
            const FVector Next=Spline->GetLocationAtSplinePoint(i+1, ESplineCoordinateSpace::World);
            const double l1=FVector2D::Distance(FVector2D(Prev.X,Prev.Y),FVector2D(Curr.X,Curr.Y));
            const double l2=FVector2D::Distance(FVector2D(Curr.X,Curr.Y),FVector2D(Next.X,Next.Y));
            if(l1<1e-6||l2<1e-6) continue;
            const FVector v1=Curr-Prev, v2=Next-Curr;
            const double dot=(v1.X*v2.X+v1.Y*v2.Y)/(l1*l2);
            const double ang=FMath::Acos(FMath::Clamp(dot,-1.0,1.0))*180.0/PI;
            MaxTurn=FMath::Max(MaxTurn,ang);
            if(ang>1.0){ double avg=(l1+l2)*0.5; double rad=avg/(2.0*FMath::Sin(ang*PI/360.0)); MinBendRadiusCm=FMath::Min(MinBendRadiusCm,rad); }
        }
        // Wrap-around
        {
            const FVector Prev=Spline->GetLocationAtSplinePoint(N-1, ESplineCoordinateSpace::World);
            const FVector Curr=Spline->GetLocationAtSplinePoint(0, ESplineCoordinateSpace::World);
            const FVector Next=Spline->GetLocationAtSplinePoint(1, ESplineCoordinateSpace::World);
            const double l1=FVector2D::Distance(FVector2D(Prev.X,Prev.Y),FVector2D(Curr.X,Curr.Y));
            const double l2=FVector2D::Distance(FVector2D(Curr.X,Curr.Y),FVector2D(Next.X,Next.Y));
            if(l1>1e-6&&l2>1e-6){
                const FVector v1=Curr-Prev, v2=Next-Curr;
                const double dot=(v1.X*v2.X+v1.Y*v2.Y)/(l1*l2);
                const double ang=FMath::Acos(FMath::Clamp(dot,-1.0,1.0))*180.0/PI;
                MaxTurn=FMath::Max(MaxTurn,ang);
                if(ang>1.0){ double avg=(l1+l2)*0.5; double rad=avg/(2.0*FMath::Sin(ang*PI/360.0)); MinBendRadiusCm=FMath::Min(MinBendRadiusCm,rad); }
            }
        }
        UE_LOG(LogTemp, Display, TEXT("JPCUSP FIXED CONTROL_POINTS=%d MAX_SLOPE=%.1f deg MAX_TURN=%.1f deg MIN_BEND_RADIUS=%.0f cm (%.1f m) TOTAL_LENGTH=%.1f cm (%.3f km)"), N, MaxSlope, MaxTurn, MinBendRadiusCm<1e11?MinBendRadiusCm:-1, MinBendRadiusCm<1e11?MinBendRadiusCm/100.0:-1, TotalLen, TotalLen/100000.0);
        for(auto& R: Fixes){ UE_LOG(LogTemp, Display, TEXT("JPCUSP CHANGED %d: angle %.1f->%.1f slopes %.1f/%.1f -> %.1f/%.1f"), R.Index, R.OldAngle, R.NewAngle, R.OldSlope0, R.OldSlope1, R.NewSlope0, R.NewSlope1); }
    }

    // Rebuild ribbon visualization from updated spline
    {
        TArray<AActor*> OldRibbon;
        for (FActorIterator It(World); It; ++It) if (It->GetActorLabel().StartsWith(TEXT("TOUR_Ribbon_"))) OldRibbon.Add(*It);
        for (AActor* A: OldRibbon) A->Destroy();
        UE_LOG(LogTemp, Display, TEXT("JPCUSP REMOVED_RIBBON_SEGMENTS=%d"), OldRibbon.Num());

        auto SampleHeightRibbon = [&](double X, double Y, double& OutZ) -> bool
        {
            const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
            if (!H.IsSet()) return false;
            OutZ = static_cast<double>(H.GetValue());
            return true;
        };
        const double SplineLenRibbon = Spline->GetSplineLength();
        constexpr double StepCm = 800.0;
        constexpr double WidthCm = 1000.0;
        constexpr double HeightOff = 200.0;
        const int32 NumSteps = FMath::Max(1, FMath::CeilToInt(SplineLenRibbon / StepCm));
        TArray<FVector> RibbonPts;
        RibbonPts.Reserve(NumSteps+1);
        for(int32 s=0; s<=NumSteps; ++s){
            const double Dist=(SplineLenRibbon*s)/NumSteps;
            const FVector SPos=Spline->GetLocationAtDistanceAlongSpline(Dist, ESplineCoordinateSpace::World);
            double Hz=0; if(!SampleHeightRibbon(SPos.X,SPos.Y,Hz)) continue;
            RibbonPts.Add(FVector(SPos.X,SPos.Y,Hz+HeightOff));
        }
        UObject* PlaneMesh = StaticLoadObject(UStaticMesh::StaticClass(), nullptr, TEXT("/Engine/BasicShapes/Plane"));
        UMaterial* RibbonMat = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
        if (!RibbonMat) RibbonMat = LoadObject<UMaterial>(nullptr, TEXT("/Engine/EngineMaterials/WorldGridMaterial"));
        int32 RibbonSegments=0;
        for(int32 i=0;i<RibbonPts.Num();++i){
            const FVector& P0=RibbonPts[i];
            const FVector& P1=RibbonPts[(i+1)%RibbonPts.Num()];
            const double SegLen=FVector::Dist(P0,P1); if(SegLen<1e-3) continue;
            const FVector Mid=(P0+P1)*0.5;
            const double Yaw=FMath::Atan2(P1.Y-P0.Y, P1.X-P0.X)*180.0/PI;
            const double LenWithOverlap=SegLen*1.08;
            AActor* SegActor=World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator(0.0,Yaw,0.0), Mid));
            if(!SegActor) continue;
            if(UStaticMeshComponent* SMC=Cast<AStaticMeshActor>(SegActor)->GetStaticMeshComponent()){
                SMC->SetStaticMesh(Cast<UStaticMesh>(PlaneMesh));
                SMC->SetWorldScale3D(FVector(LenWithOverlap/100.0, WidthCm/100.0, 1.0));
                if(RibbonMat) SMC->SetMaterial(0,RibbonMat);
                SMC->SetMobility(EComponentMobility::Movable);
                SMC->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                SMC->SetCastShadow(false);
            }
            SegActor->SetActorLabel(FString::Printf(TEXT("TOUR_Ribbon_%04d"), RibbonSegments));
            SegActor->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide/Visualization")));
            ++RibbonSegments;
        }
        UE_LOG(LogTemp, Display, TEXT("JPCUSP RIBBON_SEGMENTS=%d"), RibbonSegments);
    }

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("FixCusps failed: could not save level."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JPCUSP FIXED: 2 cusps smoothed, ribbon rebuilt."));
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::FlattenTourRoadCuspsTangents()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps refused: editor is unavailable."));
        return false;
    }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps refused: target map is not active."));
        return false;
    }
    ALandscapeProxy* Landscape = nullptr;
    int32 LandscapeCount = 0;
    AActor* GuideActor = nullptr;
    USplineComponent* Spline = nullptr;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It))
        {
            ++LandscapeCount;
            Landscape = Proxy;
        }
        if (It->GetActorLabel() == TEXT("TOUR_RoadGuide"))
        {
            GuideActor = *It;
            Spline = GuideActor->FindComponentByClass<USplineComponent>();
        }
    }
    if (LandscapeCount != 1 || !Landscape)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps refused: expected exactly 1 Landscape, found %d."), LandscapeCount);
        return false;
    }
    if (!GuideActor || !Spline)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps refused: TOUR_RoadGuide spline not found."));
        return false;
    }
    const int32 NumPoints = Spline->GetNumberOfSplinePoints();
    UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT ORIGINAL_POINTS=%d LENGTH=%.1f cm (%.3f km)"), NumPoints, Spline->GetSplineLength(), Spline->GetSplineLength()/100000.0);
    // Verify control point count unchanged (14) and positions preserved (log)
    TArray<FVector> OriginalPositions;
    for (int32 i = 0; i < NumPoints; ++i) OriginalPositions.Add(Spline->GetLocationAtSplinePoint(i, ESplineCoordinateSpace::World));
    UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT CONFIRM_POINTS=%d UNCHANGED_POSITIONS"), NumPoints);

    auto SampleHeightTan = [&](double X, double Y, double& OutZ) -> bool
    {
        const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
        if (!H.IsSet()) return false;
        OutZ = static_cast<double>(H.GetValue());
        return true;
    };

    if (NumPoints != 14)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps refused: expected 14 control points, found %d."), NumPoints);
        return false;
    }

    auto MakeBisectorTangent = [](const FVector& Incoming, const FVector& Outgoing, double Magnitude, double Z)
    {
        const FVector2D In2D(Incoming.X, Incoming.Y);
        const FVector2D Out2D(Outgoing.X, Outgoing.Y);
        const FVector2D Direction = In2D.GetSafeNormal() + Out2D.GetSafeNormal();
        const FVector2D Unit = Direction.GetSafeNormal();
        return FVector(Unit.X * Magnitude, Unit.Y * Magnitude, Z);
    };

    auto SetLocalPosition = [&](int32 Index, const FVector& Position)
    {
        Spline->SetLocationAtSplinePoint(Index, Position, ESplineCoordinateSpace::World, false);
        return true;
    };

    auto ApplyLocalFix = [&](int32 CuspIndex, double PreviousFraction, double AnchorScale,
        double CuspScale, double FollowingScale, bool bMoveFollowing, double FollowingFraction,
        double PreviousOffset, double PreviousWaypointScale)
    {
        const int32 PreviousAnchorIndex = (CuspIndex - 2 + NumPoints) % NumPoints;
        const int32 PreviousWaypointIndex = (CuspIndex - 1 + NumPoints) % NumPoints;
        const int32 FollowingWaypointIndex = (CuspIndex + 1) % NumPoints;
        const int32 NextAnchorIndex = (CuspIndex + 2) % NumPoints;
        const int32 WaypointBeforeAnchorIndex = (PreviousAnchorIndex - 1 + NumPoints) % NumPoints;

        const FVector PreviousAnchor = Spline->GetLocationAtSplinePoint(PreviousAnchorIndex, ESplineCoordinateSpace::World);
        const FVector Cusp = Spline->GetLocationAtSplinePoint(CuspIndex, ESplineCoordinateSpace::World);
        const FVector NextAnchor = Spline->GetLocationAtSplinePoint(NextAnchorIndex, ESplineCoordinateSpace::World);
        FVector FollowingWaypoint = Spline->GetLocationAtSplinePoint(FollowingWaypointIndex, ESplineCoordinateSpace::World);
        FVector PreviousWaypoint = FMath::Lerp(PreviousAnchor, Cusp, PreviousFraction);
        const FVector2D PreviousChord(Cusp.X - PreviousAnchor.X, Cusp.Y - PreviousAnchor.Y);
        const FVector2D Perpendicular(-PreviousChord.Y, PreviousChord.X);
        const FVector2D Offset = Perpendicular.GetSafeNormal() * PreviousOffset;
        PreviousWaypoint.X += Offset.X;
        PreviousWaypoint.Y += Offset.Y;
        const double PreviousSegmentLength = FVector2D(PreviousWaypoint.X - PreviousAnchor.X, PreviousWaypoint.Y - PreviousAnchor.Y).Length();
        const double CuspSegmentLength = FVector2D(Cusp.X - PreviousWaypoint.X, Cusp.Y - PreviousWaypoint.Y).Length();
        PreviousWaypoint.Z = PreviousAnchor.Z + (Cusp.Z - PreviousAnchor.Z) * PreviousSegmentLength / (PreviousSegmentLength + CuspSegmentLength);
        if (!SetLocalPosition(PreviousWaypointIndex, PreviousWaypoint)) return false;
        if (bMoveFollowing)
        {
            FollowingWaypoint = FMath::Lerp(Cusp, NextAnchor, FollowingFraction);
            if (!SetLocalPosition(FollowingWaypointIndex, FollowingWaypoint)) return false;
        }

        const FVector AdjustedPreviousWaypoint = Spline->GetLocationAtSplinePoint(PreviousWaypointIndex, ESplineCoordinateSpace::World);
        const FVector AdjustedFollowingWaypoint = Spline->GetLocationAtSplinePoint(FollowingWaypointIndex, ESplineCoordinateSpace::World);
        const FVector WaypointBeforeAnchor = Spline->GetLocationAtSplinePoint(WaypointBeforeAnchorIndex, ESplineCoordinateSpace::World);

        const FVector AnchorIncoming = PreviousAnchor - WaypointBeforeAnchor;
        const FVector AnchorOutgoing = AdjustedPreviousWaypoint - PreviousAnchor;
        const double AnchorIncomingLength = FVector2D(AnchorIncoming).Length();
        const double AnchorOutgoingLength = FVector2D(AnchorOutgoing).Length();
        const double AnchorMagnitude = FMath::Min(AnchorIncomingLength, AnchorOutgoingLength) * AnchorScale;
        const double AnchorGrade = 0.5 * (AnchorIncoming.Z / AnchorIncomingLength + AnchorOutgoing.Z / AnchorOutgoingLength);
        FVector AnchorTangent = MakeBisectorTangent(AnchorIncoming, AnchorOutgoing, AnchorMagnitude, AnchorMagnitude * AnchorGrade);
        if (CuspIndex == 6) AnchorTangent.Z *= 2.4;
        Spline->SetTangentsAtSplinePoint(PreviousAnchorIndex, AnchorTangent, AnchorTangent, ESplineCoordinateSpace::World, false);

        const FVector PreviousWaypointIncoming = AdjustedPreviousWaypoint - PreviousAnchor;
        const FVector PreviousWaypointOutgoing = Cusp - AdjustedPreviousWaypoint;
        const double PreviousWaypointIncomingLength = FVector2D(PreviousWaypointIncoming).Length();
        const double PreviousWaypointOutgoingLength = FVector2D(PreviousWaypointOutgoing).Length();
        const double PreviousWaypointMagnitude = (PreviousWaypointIncomingLength + PreviousWaypointOutgoingLength) * PreviousWaypointScale;
        const double PreviousWaypointGrade = 0.5 * (PreviousWaypointIncoming.Z / PreviousWaypointIncomingLength + PreviousWaypointOutgoing.Z / PreviousWaypointOutgoingLength);
        FVector PreviousWaypointTangent = MakeBisectorTangent(PreviousWaypointIncoming, PreviousWaypointOutgoing, PreviousWaypointMagnitude, PreviousWaypointMagnitude * PreviousWaypointGrade);
        if (CuspIndex == 6) PreviousWaypointTangent.Z *= 0.6;
        Spline->SetTangentsAtSplinePoint(PreviousWaypointIndex, PreviousWaypointTangent, PreviousWaypointTangent, ESplineCoordinateSpace::World, false);

        const FVector CuspIncoming = Cusp - AdjustedPreviousWaypoint;
        const FVector CuspOutgoing = AdjustedFollowingWaypoint - Cusp;
        const double CuspIncomingLength = FVector2D(CuspIncoming).Length();
        const double CuspOutgoingLength = FVector2D(CuspOutgoing).Length();
        const double CuspMagnitude = (CuspIncomingLength + CuspOutgoingLength) * CuspScale;
        const double CuspGrade = 0.5 * (CuspIncoming.Z / CuspIncomingLength + CuspOutgoing.Z / CuspOutgoingLength);
        FVector CuspTangent = MakeBisectorTangent(CuspIncoming, CuspOutgoing, CuspMagnitude, CuspMagnitude * CuspGrade);
        if (CuspIndex == 6) CuspTangent.Z *= 2.4;
        Spline->SetTangentsAtSplinePoint(CuspIndex, CuspTangent, CuspTangent, ESplineCoordinateSpace::World, false);

        const FVector FollowingIncoming = AdjustedFollowingWaypoint - Cusp;
        const FVector FollowingOutgoing = NextAnchor - AdjustedFollowingWaypoint;
        const double FollowingIncomingLength = FVector2D(FollowingIncoming).Length();
        const double FollowingOutgoingLength = FVector2D(FollowingOutgoing).Length();
        const double FollowingMagnitude = (FollowingIncomingLength + FollowingOutgoingLength) * FollowingScale;
        const double FollowingGrade = 0.5 * (FollowingIncoming.Z / FollowingIncomingLength + FollowingOutgoing.Z / FollowingOutgoingLength);
        const FVector FollowingTangent = MakeBisectorTangent(FollowingIncoming, FollowingOutgoing, FollowingMagnitude, FollowingMagnitude * FollowingGrade);
        Spline->SetTangentsAtSplinePoint(FollowingWaypointIndex, FollowingTangent, FollowingTangent, ESplineCoordinateSpace::World, false);
        return true;
    };

    if (!ApplyLocalFix(6, 0.65, 1.50, 0.40, 0.30, false, 0.0, -15000.0, 0.70)
        || !ApplyLocalFix(12, 0.55, 0.70, 0.55, 0.55, true, 0.425, 0.0, 0.50))
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps failed: a local waypoint was outside the Landscape."));
        return false;
    }
    Spline->UpdateSpline();

    TArray<int32> ChangedPositionIndices;
    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        const FVector Position = Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World);
        if (!OriginalPositions[Index].Equals(Position, 1.0)) ChangedPositionIndices.Add(Index);
    }
    const bool bExpectedPositionChanges = ChangedPositionIndices.IsEmpty()
        || ChangedPositionIndices == TArray<int32>({5, 11, 13});
    UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT POSITION_CHANGES=%s EXPECTED=NONE_OR_5,11,13_ONLY"),
        *FString::JoinBy(ChangedPositionIndices, TEXT(","), [](int32 Index) { return FString::FromInt(Index); }));
    if (!bExpectedPositionChanges)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps failed: unexpected control-point position change."));
        return false;
    }

    const double SplineLength = Spline->GetSplineLength();
    constexpr double VerificationStepCm = 800.0;
    const int32 VerificationSteps = FMath::Max(3, FMath::CeilToInt(SplineLength / VerificationStepCm));
    TArray<FVector> Dense;
    Dense.Reserve(VerificationSteps);
    for (int32 Step = 0; Step < VerificationSteps; ++Step)
    {
        Dense.Add(Spline->GetLocationAtDistanceAlongSpline(SplineLength * Step / VerificationSteps, ESplineCoordinateSpace::World));
    }

    auto Orientation = [](const FVector2D& P, const FVector2D& Q, const FVector2D& R)
    {
        const double Value = (Q.Y - P.Y) * (R.X - Q.X) - (Q.X - P.X) * (R.Y - Q.Y);
        if (FMath::IsNearlyZero(Value, 1e-6)) return 0;
        return Value > 0.0 ? 1 : 2;
    };
    auto Intersects = [&](const FVector2D& P1, const FVector2D& Q1, const FVector2D& P2, const FVector2D& Q2)
    {
        return Orientation(P1, Q1, P2) != Orientation(P1, Q1, Q2)
            && Orientation(P2, Q2, P1) != Orientation(P2, Q2, Q1);
    };
    bool bSelfIntersect = false;
    for (int32 First = 0; First < Dense.Num() && !bSelfIntersect; ++First)
    {
        const int32 FirstNext = (First + 1) % Dense.Num();
        for (int32 Second = First + 2; Second < Dense.Num(); ++Second)
        {
            const int32 SecondNext = (Second + 1) % Dense.Num();
            if (First == 0 && SecondNext == 0) continue;
            if (Intersects(FVector2D(Dense[First]), FVector2D(Dense[FirstNext]), FVector2D(Dense[Second]), FVector2D(Dense[SecondNext])))
            {
                bSelfIntersect = true;
                break;
            }
        }
    }

    double MaxSlope = 0.0;
    FVector MaxSlopePosition = FVector::ZeroVector;
    double GlobalMinRadius = TNumericLimits<double>::Max();
    bool bLoopback = false;
    for (int32 Index = 0; Index < Dense.Num(); ++Index)
    {
        const FVector& Previous = Dense[(Index - 1 + Dense.Num()) % Dense.Num()];
        const FVector& Current = Dense[Index];
        const FVector& Next = Dense[(Index + 1) % Dense.Num()];
        const FVector2D Incoming(Current.X - Previous.X, Current.Y - Previous.Y);
        const FVector2D Outgoing(Next.X - Current.X, Next.Y - Current.Y);
        const double IncomingLength = Incoming.Length();
        const double OutgoingLength = Outgoing.Length();
        if (IncomingLength < 1.0 || OutgoingLength < 1.0) continue;
        const double Angle = FMath::Acos(FMath::Clamp(FVector2D::DotProduct(Incoming, Outgoing) / (IncomingLength * OutgoingLength), -1.0, 1.0));
        if (Angle > FMath::DegreesToRadians(150.0)) bLoopback = true;
        if (Angle > 1e-6)
        {
            GlobalMinRadius = FMath::Min(GlobalMinRadius, (IncomingLength + OutgoingLength) * 0.25 / FMath::Sin(Angle * 0.5));
        }
        const double Slope = FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Next.Z - Current.Z), OutgoingLength));
        if (Slope > MaxSlope)
        {
            MaxSlope = Slope;
            MaxSlopePosition = Current;
        }
    }

    auto LocalMinRadius = [&](double StartInputKey)
    {
        TArray<FVector> Points;
        Points.Reserve(161);
        for (int32 Step = 0; Step <= 160; ++Step)
        {
            Points.Add(Spline->GetLocationAtSplineInputKey(StartInputKey + Step / 40.0, ESplineCoordinateSpace::World));
        }
        double Minimum = TNumericLimits<double>::Max();
        for (int32 Index = 1; Index + 1 < Points.Num(); ++Index)
        {
            const FVector2D Incoming(Points[Index].X - Points[Index - 1].X, Points[Index].Y - Points[Index - 1].Y);
            const FVector2D Outgoing(Points[Index + 1].X - Points[Index].X, Points[Index + 1].Y - Points[Index].Y);
            const double IncomingLength = Incoming.Length();
            const double OutgoingLength = Outgoing.Length();
            if (IncomingLength < 1.0 || OutgoingLength < 1.0) continue;
            const double Angle = FMath::Acos(FMath::Clamp(FVector2D::DotProduct(Incoming, Outgoing) / (IncomingLength * OutgoingLength), -1.0, 1.0));
            if (Angle > 1e-6) Minimum = FMath::Min(Minimum, (IncomingLength + OutgoingLength) * 0.25 / FMath::Sin(Angle * 0.5));
        }
        return Minimum;
    };
    const double UpperRadius = LocalMinRadius(4.0);
    const double LowerRadius = LocalMinRadius(10.0);
    double MaxControlSlope = 0.0;
    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        const FVector Current = Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World);
        const FVector Next = Spline->GetLocationAtSplinePoint((Index + 1) % NumPoints, ESplineCoordinateSpace::World);
        const double HorizontalLength = FVector2D(Next.X - Current.X, Next.Y - Current.Y).Length();
        if (HorizontalLength > 1.0)
        {
            MaxControlSlope = FMath::Max(MaxControlSlope,
                FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Next.Z - Current.Z), HorizontalLength)));
        }
    }
    UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT VERIFY SELF_INTERSECT=%s LOOPBACK=%s MAX_CONTROL_SLOPE=%.2f deg DENSE_SPLINE_SLOPE=%.2f deg UPPER_RADIUS=%.0f cm (%.1f m) LOWER_RADIUS=%.0f cm (%.1f m) GLOBAL_MIN_RADIUS=%.0f cm (%.1f m) SPLINE_LENGTH=%.1f cm (%.3f km)"),
        bSelfIntersect ? TEXT("YES") : TEXT("NO"), bLoopback ? TEXT("YES") : TEXT("NO"), MaxControlSlope, MaxSlope,
        UpperRadius, UpperRadius / 100.0, LowerRadius, LowerRadius / 100.0,
        GlobalMinRadius, GlobalMinRadius / 100.0, SplineLength, SplineLength / 100000.0);
    UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT MAX_SLOPE_POSITION=(%.0f,%.0f,%.0f)"), MaxSlopePosition.X, MaxSlopePosition.Y, MaxSlopePosition.Z);
    if (bSelfIntersect || bLoopback || MaxControlSlope > 15.0 || UpperRadius < 5000.0 || LowerRadius < 5000.0)
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps failed verification; map will not be saved."));
        return false;
    }

    // Rebuild ribbon from updated spline (keep positions, only tangents changed)
    {
        TArray<AActor*> OldRibbon;
        for (FActorIterator It(World); It; ++It) if (It->GetActorLabel().StartsWith(TEXT("TOUR_Ribbon_"))) OldRibbon.Add(*It);
        for (AActor* A: OldRibbon) A->Destroy();
        UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT REMOVED_RIBBON_SEGMENTS=%d"), OldRibbon.Num());
        auto SampleHeightRibbon = [&](double X, double Y, double& OutZ) -> bool
        {
            const TOptional<float> H = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
            if (!H.IsSet()) return false;
            OutZ = static_cast<double>(H.GetValue());
            return true;
        };
        const double SplineLenRibbon = Spline->GetSplineLength();
        constexpr double StepCm = 800.0;
        constexpr double WidthCm = 1000.0;
        constexpr double HeightOff = 200.0;
        const int32 NumSteps = FMath::Max(1, FMath::CeilToInt(SplineLenRibbon / StepCm));
        TArray<FVector> RibbonPts;
        RibbonPts.Reserve(NumSteps+1);
        for(int32 s=0; s<=NumSteps; ++s){
            const double Dist=(SplineLenRibbon*s)/NumSteps;
            const FVector SPos=Spline->GetLocationAtDistanceAlongSpline(Dist, ESplineCoordinateSpace::World);
            double Hz=0; if(!SampleHeightRibbon(SPos.X,SPos.Y,Hz)) continue;
            RibbonPts.Add(FVector(SPos.X,SPos.Y,Hz+HeightOff));
        }
        UObject* PlaneMesh = StaticLoadObject(UStaticMesh::StaticClass(), nullptr, TEXT("/Engine/BasicShapes/Plane"));
        UMaterial* RibbonMat = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
        if (!RibbonMat) RibbonMat = LoadObject<UMaterial>(nullptr, TEXT("/Engine/EngineMaterials/WorldGridMaterial"));
        int32 RibbonSegments=0;
        for(int32 i=0;i<RibbonPts.Num();++i){
            const FVector& P0=RibbonPts[i];
            const FVector& P1=RibbonPts[(i+1)%RibbonPts.Num()];
            const double SegLen=FVector::Dist(P0,P1); if(SegLen<1e-3) continue;
            const FVector Mid=(P0+P1)*0.5;
            const double Yaw=FMath::Atan2(P1.Y-P0.Y, P1.X-P0.X)*180.0/PI;
            const double LenWithOverlap=SegLen*1.08;
            AActor* SegActor=World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), FTransform(FRotator(0.0,Yaw,0.0), Mid));
            if(!SegActor) continue;
            if(UStaticMeshComponent* SMC=Cast<AStaticMeshActor>(SegActor)->GetStaticMeshComponent()){
                SMC->SetStaticMesh(Cast<UStaticMesh>(PlaneMesh));
                SMC->SetWorldScale3D(FVector(LenWithOverlap/100.0, WidthCm/100.0, 1.0));
                if(RibbonMat) SMC->SetMaterial(0,RibbonMat);
                SMC->SetMobility(EComponentMobility::Movable);
                SMC->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                SMC->SetCastShadow(false);
            }
            SegActor->SetActorLabel(FString::Printf(TEXT("TOUR_Ribbon_%04d"), RibbonSegments));
            SegActor->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide/Visualization")));
            ++RibbonSegments;
        }
        UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT RIBBON_SEGMENTS=%d"), RibbonSegments);
    }

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("FlattenCusps failed: could not save level."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JPCUSP_TANGENT FIXED: 2 cusps flattened via tangents, ribbon rebuilt."));
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::FixTourRoadWaterCrossing()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX refused: target map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    USplineComponent* Spline = nullptr;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It)) Landscape = Proxy;
        if (It->GetActorLabel() == TEXT("TOUR_RoadGuide")) Spline = It->FindComponentByClass<USplineComponent>();
    }
    if (!Landscape || !Spline || Spline->GetNumberOfSplinePoints() != 14)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX refused: expected one Landscape and a 14-point TOUR_RoadGuide."));
        return false;
    }

    constexpr double WaterLevel = 5000.0;
    constexpr double RequiredTerrainHeight = 5300.0;
    constexpr double HeightOffset = 80.0;
    const int32 NumPoints = Spline->GetNumberOfSplinePoints();
    TArray<FVector> OriginalPositions;
    TArray<FVector> OriginalArriveTangents;
    TArray<FVector> OriginalLeaveTangents;
    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        OriginalPositions.Add(Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalArriveTangents.Add(Spline->GetArriveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalLeaveTangents.Add(Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World));
    }

    TMap<FString, FVector> OriginalMarkerPositions;
    for (FActorIterator It(World); It; ++It)
    {
        if (It->GetActorLabel().StartsWith(TEXT("JP93_"))) OriginalMarkerPositions.Add(It->GetActorLabel(), It->GetActorLocation());
    }
    if (OriginalMarkerPositions.Num() != 10)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX refused: expected 10 JP93 markers, found %d."), OriginalMarkerPositions.Num());
        return false;
    }

    TMap<int32, FVector> UnaffectedMidpoints;
    for (int32 Segment = 0; Segment < NumPoints; ++Segment)
    {
        if (Segment == 2 || Segment == 3 || Segment == 8 || Segment == 9) continue;
        UnaffectedMidpoints.Add(Segment, Spline->GetLocationAtSplineInputKey(Segment + 0.5, ESplineCoordinateSpace::World));
    }

    auto RestoreSpline = [&]()
    {
        for (int32 Index = 0; Index < NumPoints; ++Index)
        {
            Spline->SetLocationAtSplinePoint(Index, OriginalPositions[Index], ESplineCoordinateSpace::World, false);
            Spline->SetTangentsAtSplinePoint(Index, OriginalArriveTangents[Index], OriginalLeaveTangents[Index], ESplineCoordinateSpace::World, false);
        }
        Spline->UpdateSpline();
    };

    auto SetCandidate = [&](int32 WaypointIndex, double X, double Y, double TangentScale)
    {
        const int32 PreviousAnchorIndex = WaypointIndex - 1;
        const int32 NextAnchorIndex = WaypointIndex + 1;
        const FVector PreviousAnchor = OriginalPositions[PreviousAnchorIndex];
        const FVector NextAnchor = OriginalPositions[NextAnchorIndex];
        const double PreviousLength = FVector2D::Distance(FVector2D(PreviousAnchor), FVector2D(X, Y));
        const double NextLength = FVector2D::Distance(FVector2D(X, Y), FVector2D(NextAnchor));
        const double Z = PreviousAnchor.Z + (NextAnchor.Z - PreviousAnchor.Z) * PreviousLength / (PreviousLength + NextLength);
        const FVector Position(X, Y, Z);
        const FVector Chord = NextAnchor - PreviousAnchor;
        const FVector Tangent = Chord * TangentScale;
        Spline->SetLocationAtSplinePoint(WaypointIndex, Position, ESplineCoordinateSpace::World, false);
        Spline->SetTangentsAtSplinePoint(WaypointIndex, Tangent, Tangent, ESplineCoordinateSpace::World, false);
        Spline->UpdateSpline();
    };
    auto SetPoint10ArriveTangent = [&](double Scale)
    {
        const FVector Point9Position = Spline->GetLocationAtSplinePoint(9, ESplineCoordinateSpace::World);
        const FVector Point10Position = Spline->GetLocationAtSplinePoint(10, ESplineCoordinateSpace::World);
        const FVector ArriveTangent = (Point10Position - Point9Position) * Scale;
        Spline->SetTangentsAtSplinePoint(10, ArriveTangent, OriginalLeaveTangents[10], ESplineCoordinateSpace::World, false);
        Spline->UpdateSpline();
    };

    struct FLocalWaterMetrics
    {
        double MinimumTerrain = TNumericLimits<double>::Max();
        double MaximumSlope = 0.0;
        double MinimumRadius = TNumericLimits<double>::Max();
        double MinimumRadiusKey = 0.0;
        int32 WaterSamples = 0;
    };
    auto EvaluateLocal = [&](double StartKey, double EndKey)
    {
        constexpr int32 StepsPerSegment = 200;
        const int32 Steps = FMath::RoundToInt((EndKey - StartKey) * StepsPerSegment);
        TArray<FVector> Samples;
        Samples.Reserve(Steps + 1);
        FLocalWaterMetrics Metrics;
        for (int32 Step = 0; Step <= Steps; ++Step)
        {
            const double Key = FMath::Lerp(StartKey, EndKey, static_cast<double>(Step) / Steps);
            const FVector Position = Spline->GetLocationAtSplineInputKey(Key, ESplineCoordinateSpace::World);
            Samples.Add(Position);
            const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Position.X, Position.Y, 0.0));
            if (!Height.IsSet())
            {
                Metrics.MinimumTerrain = -1.0;
                ++Metrics.WaterSamples;
                continue;
            }
            Metrics.MinimumTerrain = FMath::Min(Metrics.MinimumTerrain, static_cast<double>(Height.GetValue()));
            if (Height.GetValue() <= WaterLevel) ++Metrics.WaterSamples;
        }
        for (int32 Index = 1; Index + 1 < Samples.Num(); ++Index)
        {
            const FVector& Previous = Samples[Index - 1];
            const FVector& Current = Samples[Index];
            const FVector& Next = Samples[Index + 1];
            const FVector2D Incoming(Current.X - Previous.X, Current.Y - Previous.Y);
            const FVector2D Outgoing(Next.X - Current.X, Next.Y - Current.Y);
            const double IncomingLength = Incoming.Length();
            const double OutgoingLength = Outgoing.Length();
            if (IncomingLength < 1.0 || OutgoingLength < 1.0) continue;
            Metrics.MaximumSlope = FMath::Max(Metrics.MaximumSlope,
                FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Next.Z - Current.Z), OutgoingLength)));
            const double Angle = FMath::Acos(FMath::Clamp(FVector2D::DotProduct(Incoming, Outgoing) / (IncomingLength * OutgoingLength), -1.0, 1.0));
            if (Angle > 1e-6)
            {
                const double Radius = (IncomingLength + OutgoingLength) * 0.25 / FMath::Sin(Angle * 0.5);
                if (Radius < Metrics.MinimumRadius)
                {
                    Metrics.MinimumRadius = Radius;
                    Metrics.MinimumRadiusKey = FMath::Lerp(StartKey, EndKey, static_cast<double>(Index) / Steps);
                }
            }
        }
        return Metrics;
    };

    struct FWaypointCandidate
    {
        FVector Position = FVector::ZeroVector;
        double TangentScale = 0.0;
        double BoundaryScale = 0.0;
        double Movement = TNumericLimits<double>::Max();
        FLocalWaterMetrics Metrics;
        bool bValid = false;
    };
    auto FindCandidate = [&](int32 WaypointIndex, double MinX, double MaxX, double MinY, double MaxY,
        double GridStep, double StartKey, double EndKey)
    {
        FWaypointCandidate Best;
        FWaypointCandidate BestDiagnostic;
        for (double X = MinX; X <= MaxX; X += GridStep)
        {
            for (double Y = MinY; Y <= MaxY; Y += GridStep)
            {
                const TOptional<float> CandidateHeight = Landscape->GetHeightAtLocation(FVector(X, Y, 0.0));
                if (!CandidateHeight.IsSet() || CandidateHeight.GetValue() < RequiredTerrainHeight) continue;
                const int32 MinimumScaleStep = WaypointIndex == 9 ? 6 : 3;
                const int32 MaximumScaleStep = WaypointIndex == 9 ? 14 : 10;
                for (int32 ScaleStep = MinimumScaleStep; ScaleStep <= MaximumScaleStep; ++ScaleStep)
                {
                    const double TangentScale = ScaleStep * 0.1;
                    const int32 MinimumBoundaryStep = WaypointIndex == 9 ? 3 : 0;
                    const int32 MaximumBoundaryStep = WaypointIndex == 9 ? 10 : 0;
                    for (int32 BoundaryStep = MinimumBoundaryStep; BoundaryStep <= MaximumBoundaryStep; ++BoundaryStep)
                    {
                        const double BoundaryScale = BoundaryStep * 0.1;
                        SetCandidate(WaypointIndex, X, Y, TangentScale);
                        if (WaypointIndex == 9) SetPoint10ArriveTangent(BoundaryScale);
                        const FLocalWaterMetrics Metrics = EvaluateLocal(StartKey, EndKey);
                        const double Movement = FVector2D::Distance(FVector2D(X, Y), FVector2D(OriginalPositions[WaypointIndex]));
                        const bool bValid = Metrics.WaterSamples == 0
                            && Metrics.MinimumTerrain >= RequiredTerrainHeight
                            && Metrics.MaximumSlope <= 15.0
                            && Metrics.MinimumRadius >= 5000.0;
                        if (bValid && (!Best.bValid || Movement < Best.Movement
                            || (FMath::IsNearlyEqual(Movement, Best.Movement, 1.0) && Metrics.MinimumTerrain > Best.Metrics.MinimumTerrain)))
                        {
                            Best = {FVector(X, Y, CandidateHeight.GetValue() + HeightOffset), TangentScale, BoundaryScale, Movement, Metrics, true};
                        }
                        const bool bDiagnosticEligible = Metrics.WaterSamples == 0
                            && Metrics.MinimumTerrain >= RequiredTerrainHeight
                            && Metrics.MaximumSlope <= 15.0;
                        if (bDiagnosticEligible && (!BestDiagnostic.bValid || Metrics.MinimumRadius > BestDiagnostic.Metrics.MinimumRadius))
                        {
                            BestDiagnostic = {FVector(X, Y, CandidateHeight.GetValue() + HeightOffset), TangentScale, BoundaryScale, Movement, Metrics, true};
                        }
                    }
                }
            }
        }
        RestoreSpline();
        if (!Best.bValid)
        {
            UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX no valid candidate for point %d. Best diagnostic pos=(%.0f,%.0f) scale=%.2f boundary=%.2f terrain=%.1f slope=%.2f radius=%.0f radius_key=%.3f water=%d."),
                WaypointIndex, BestDiagnostic.Position.X, BestDiagnostic.Position.Y, BestDiagnostic.TangentScale, BestDiagnostic.BoundaryScale,
                BestDiagnostic.Metrics.MinimumTerrain, BestDiagnostic.Metrics.MaximumSlope,
                BestDiagnostic.Metrics.MinimumRadius, BestDiagnostic.Metrics.MinimumRadiusKey, BestDiagnostic.Metrics.WaterSamples);
        }
        return Best;
    };

    const FWaypointCandidate Point3 = FindCandidate(3, 210000.0, 222500.0, 290000.0, 300000.0, 1250.0, 2.05, 3.95);
    if (!Point3.bValid) return false;
    const FWaypointCandidate Point9 = FindCandidate(9, 200000.0, 225000.0, 140000.0, 150000.0, 2500.0, 8.05, 9.95);
    if (!Point9.bValid) return false;

    SetCandidate(3, Point3.Position.X, Point3.Position.Y, Point3.TangentScale);
    SetCandidate(9, Point9.Position.X, Point9.Position.Y, Point9.TangentScale);
    SetPoint10ArriveTangent(Point9.BoundaryScale);
    const FLocalWaterMetrics Point3Final = EvaluateLocal(2.05, 3.95);
    const FLocalWaterMetrics Point9Final = EvaluateLocal(8.05, 9.95);

    bool bMarkersUnchanged = true;
    int32 MarkerCount = 0;
    for (FActorIterator It(World); It; ++It)
    {
        if (!It->GetActorLabel().StartsWith(TEXT("JP93_"))) continue;
        ++MarkerCount;
        const FVector* Original = OriginalMarkerPositions.Find(It->GetActorLabel());
        if (!Original || !Original->Equals(It->GetActorLocation(), 0.1)) bMarkersUnchanged = false;
    }

    TArray<int32> ChangedControls;
    bool bTangentsLimited = true;
    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        const FVector Position = Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World);
        if (!Position.Equals(OriginalPositions[Index], 0.1)) ChangedControls.Add(Index);
        if (Index != 3 && Index != 9 && Index != 10)
        {
            if (!Spline->GetArriveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World).Equals(OriginalArriveTangents[Index], 0.1)
                || !Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World).Equals(OriginalLeaveTangents[Index], 0.1))
            {
                bTangentsLimited = false;
            }
        }
        else if (Index == 10
            && !Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World).Equals(OriginalLeaveTangents[Index], 0.1))
        {
            bTangentsLimited = false;
        }
    }
    bool bOtherSectionsUnchanged = true;
    for (const TPair<int32, FVector>& Pair : UnaffectedMidpoints)
    {
        if (!Pair.Value.Equals(Spline->GetLocationAtSplineInputKey(Pair.Key + 0.5, ESplineCoordinateSpace::World), 0.1))
        {
            bOtherSectionsUnchanged = false;
        }
    }

    const double SplineLength = Spline->GetSplineLength();
    const int32 TerrainSteps = FMath::Max(1, FMath::CeilToInt(SplineLength / 250.0));
    double MinimumTerrain = TNumericLimits<double>::Max();
    int32 WaterSamples = 0;
    for (int32 Step = 0; Step < TerrainSteps; ++Step)
    {
        const FVector Position = Spline->GetLocationAtDistanceAlongSpline(SplineLength * Step / TerrainSteps, ESplineCoordinateSpace::World);
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Position.X, Position.Y, 0.0));
        if (!Height.IsSet())
        {
            ++WaterSamples;
            MinimumTerrain = -1.0;
            continue;
        }
        MinimumTerrain = FMath::Min(MinimumTerrain, static_cast<double>(Height.GetValue()));
        if (Height.GetValue() <= WaterLevel) ++WaterSamples;
    }

    const int32 GeometrySteps = FMath::Max(3, FMath::CeilToInt(SplineLength / 800.0));
    TArray<FVector> Dense;
    Dense.Reserve(GeometrySteps);
    for (int32 Step = 0; Step < GeometrySteps; ++Step)
    {
        Dense.Add(Spline->GetLocationAtDistanceAlongSpline(SplineLength * Step / GeometrySteps, ESplineCoordinateSpace::World));
    }
    auto Orientation = [](const FVector2D& P, const FVector2D& Q, const FVector2D& R)
    {
        const double Value = (Q.Y - P.Y) * (R.X - Q.X) - (Q.X - P.X) * (R.Y - Q.Y);
        if (FMath::IsNearlyZero(Value, 1e-6)) return 0;
        return Value > 0.0 ? 1 : 2;
    };
    auto Intersects = [&](const FVector2D& P1, const FVector2D& Q1, const FVector2D& P2, const FVector2D& Q2)
    {
        return Orientation(P1, Q1, P2) != Orientation(P1, Q1, Q2)
            && Orientation(P2, Q2, P1) != Orientation(P2, Q2, Q1);
    };
    bool bSelfIntersect = false;
    bool bLoopback = false;
    double MaxSlope = 0.0;
    for (int32 First = 0; First < Dense.Num() && !bSelfIntersect; ++First)
    {
        const int32 FirstNext = (First + 1) % Dense.Num();
        for (int32 Second = First + 2; Second < Dense.Num(); ++Second)
        {
            const int32 SecondNext = (Second + 1) % Dense.Num();
            if (First == 0 && SecondNext == 0) continue;
            if (Intersects(FVector2D(Dense[First]), FVector2D(Dense[FirstNext]), FVector2D(Dense[Second]), FVector2D(Dense[SecondNext])))
            {
                bSelfIntersect = true;
                break;
            }
        }
    }
    for (int32 Index = 0; Index < Dense.Num(); ++Index)
    {
        const FVector& Previous = Dense[(Index - 1 + Dense.Num()) % Dense.Num()];
        const FVector& Current = Dense[Index];
        const FVector& Next = Dense[(Index + 1) % Dense.Num()];
        const FVector2D Incoming(Current.X - Previous.X, Current.Y - Previous.Y);
        const FVector2D Outgoing(Next.X - Current.X, Next.Y - Current.Y);
        const double IncomingLength = Incoming.Length();
        const double OutgoingLength = Outgoing.Length();
        if (IncomingLength < 1.0 || OutgoingLength < 1.0) continue;
        const double Angle = FMath::Acos(FMath::Clamp(FVector2D::DotProduct(Incoming, Outgoing) / (IncomingLength * OutgoingLength), -1.0, 1.0));
        if (Angle > FMath::DegreesToRadians(150.0)) bLoopback = true;
        MaxSlope = FMath::Max(MaxSlope,
            FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Next.Z - Current.Z), OutgoingLength)));
    }

    const bool bControlsLimited = ChangedControls == TArray<int32>({3, 9});
    const bool bValid = WaterSamples == 0 && MinimumTerrain >= RequiredTerrainHeight
        && !bSelfIntersect && !bLoopback && MaxSlope <= 15.0
        && Point3Final.MinimumRadius >= 5000.0 && Point9Final.MinimumRadius >= 5000.0
        && bMarkersUnchanged && MarkerCount == OriginalMarkerPositions.Num()
        && bControlsLimited && bTangentsLimited && bOtherSectionsUnchanged;
    UE_LOG(LogTemp, Display, TEXT("JPWATER_FIX VERIFY CHANGED_CONTROLS=%s MIN_TERRAIN=%.1f CLEARANCE=%.1f WATER_SAMPLES=%d SELF_INTERSECT=%s LOOPBACK=%s MAX_SLOPE=%.2f POINT3_RADIUS=%.0f POINT9_RADIUS=%.0f LENGTH=%.1f MARKERS_UNCHANGED=%s OTHER_SECTIONS_UNCHANGED=%s"),
        *FString::JoinBy(ChangedControls, TEXT(","), [](int32 Index) { return FString::FromInt(Index); }),
        MinimumTerrain, MinimumTerrain - WaterLevel, WaterSamples,
        bSelfIntersect ? TEXT("YES") : TEXT("NO"), bLoopback ? TEXT("YES") : TEXT("NO"), MaxSlope,
        Point3Final.MinimumRadius, Point9Final.MinimumRadius, SplineLength,
        bMarkersUnchanged ? TEXT("YES") : TEXT("NO"), bOtherSectionsUnchanged ? TEXT("YES") : TEXT("NO"));
    UE_LOG(LogTemp, Display, TEXT("JPWATER_FIX POINT3 OLD=(%.0f,%.0f) NEW=(%.0f,%.0f) SCALE=%.2f LOCAL_MIN_TERRAIN=%.1f MOVEMENT=%.0f"),
        OriginalPositions[3].X, OriginalPositions[3].Y, Point3.Position.X, Point3.Position.Y,
        Point3.TangentScale, Point3Final.MinimumTerrain, Point3.Movement);
    UE_LOG(LogTemp, Display, TEXT("JPWATER_FIX POINT9 OLD=(%.0f,%.0f) NEW=(%.0f,%.0f) SCALE=%.2f BOUNDARY_SCALE=%.2f LOCAL_MIN_TERRAIN=%.1f MOVEMENT=%.0f"),
        OriginalPositions[9].X, OriginalPositions[9].Y, Point9.Position.X, Point9.Position.Y,
        Point9.TangentScale, Point9.BoundaryScale, Point9Final.MinimumTerrain, Point9.Movement);
    if (!bValid)
    {
        RestoreSpline();
        UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX failed verification; map will not be saved."));
        return false;
    }

    TArray<AActor*> OldRibbon;
    for (FActorIterator It(World); It; ++It)
    {
        if (It->GetActorLabel().StartsWith(TEXT("TOUR_Ribbon_"))) OldRibbon.Add(*It);
    }
    for (AActor* Actor : OldRibbon) Actor->Destroy();

    const double RibbonStep = 800.0;
    const int32 RibbonSteps = FMath::Max(1, FMath::CeilToInt(SplineLength / RibbonStep));
    TArray<FVector> RibbonPoints;
    RibbonPoints.Reserve(RibbonSteps);
    for (int32 Step = 0; Step < RibbonSteps; ++Step)
    {
        const FVector Position = Spline->GetLocationAtDistanceAlongSpline(SplineLength * Step / RibbonSteps, ESplineCoordinateSpace::World);
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Position.X, Position.Y, 0.0));
        if (Height.IsSet()) RibbonPoints.Add(FVector(Position.X, Position.Y, Height.GetValue() + 200.0));
    }
    UStaticMesh* PlaneMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane"));
    UMaterial* RibbonMaterial = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/TourRoad/MK_TourRibbon"));
    if (!RibbonMaterial) RibbonMaterial = LoadObject<UMaterial>(nullptr, TEXT("/Game/Temp/Markers/MK_JP1993"));
    int32 RibbonSegments = 0;
    for (int32 Index = 0; Index < RibbonPoints.Num(); ++Index)
    {
        const FVector& Start = RibbonPoints[Index];
        const FVector& End = RibbonPoints[(Index + 1) % RibbonPoints.Num()];
        const double SegmentLength = FVector::Distance(Start, End);
        if (SegmentLength < 1.0) continue;
        const double Yaw = FMath::RadiansToDegrees(FMath::Atan2(End.Y - Start.Y, End.X - Start.X));
        AStaticMeshActor* Segment = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
            FTransform(FRotator(0.0, Yaw, 0.0), (Start + End) * 0.5));
        if (!Segment) continue;
        UStaticMeshComponent* Mesh = Segment->GetStaticMeshComponent();
        Mesh->SetStaticMesh(PlaneMesh);
        Mesh->SetWorldScale3D(FVector(SegmentLength * 1.08 / 100.0, 10.0, 1.0));
        if (RibbonMaterial) Mesh->SetMaterial(0, RibbonMaterial);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetCastShadow(false);
        Segment->SetActorLabel(FString::Printf(TEXT("TOUR_Ribbon_%04d"), RibbonSegments));
        Segment->SetFolderPath(FName(TEXT("JP1993_Layout/TourRoad_Guide/Visualization")));
        ++RibbonSegments;
    }
    UE_LOG(LogTemp, Display, TEXT("JPWATER_FIX RIBBON_REMOVED=%d RIBBON_REBUILT=%d"), OldRibbon.Num(), RibbonSegments);

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_FIX failed to save target map."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JPWATER_FIX SUCCESS: shoreline repair saved."));
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::BuildTourRoadVisualPass()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL refused: target map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    USplineComponent* Spline = nullptr;
    TArray<AActor*> RibbonActors;
    TArray<AActor*> ExistingFinalActors;
    TMap<FString, FVector> MarkerPositions;
    for (FActorIterator It(World); It; ++It)
    {
        const FString Label = It->GetActorLabel();
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It)) Landscape = Proxy;
        if (Label == TEXT("TOUR_RoadGuide")) Spline = It->FindComponentByClass<USplineComponent>();
        if (Label.StartsWith(TEXT("TOUR_Ribbon_"))) RibbonActors.Add(*It);
        if (Label.StartsWith(TEXT("TOUR_FinalRoad_")) || Label.StartsWith(TEXT("TOUR_GuideTrack_"))) ExistingFinalActors.Add(*It);
        if (Label.StartsWith(TEXT("JP93_"))) MarkerPositions.Add(Label, It->GetActorLocation());
    }
    if (!Landscape || !Spline || Spline->GetNumberOfSplinePoints() != 14 || MarkerPositions.Num() != 10)
    {
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL refused: expected Landscape, 14-point guide, and 10 JP93 markers."));
        return false;
    }

    UStaticMesh* PlaneMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Plane"));
    UStaticMesh* CubeMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube"));
    UMaterialInterface* AsphaltMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Temp/TourRoad_Final/M_TourRoad_Asphalt"));
    UMaterialInterface* TrackMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Temp/TourRoad_Final/M_TourGuideTrack_Metal"));
    if (!PlaneMesh || !CubeMesh || !AsphaltMaterial || !TrackMaterial)
    {
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL refused: road meshes or temporary materials are missing."));
        return false;
    }

    const int32 NumPoints = Spline->GetNumberOfSplinePoints();
    TArray<FVector> OriginalPositions;
    TArray<FVector> OriginalArriveTangents;
    TArray<FVector> OriginalLeaveTangents;
    TArray<ESplinePointType::Type> OriginalPointTypes;
    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        OriginalPositions.Add(Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalArriveTangents.Add(Spline->GetArriveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalLeaveTangents.Add(Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalPointTypes.Add(Spline->GetSplinePointType(Index));
    }
    const bool bOriginalClosedLoop = Spline->IsClosedLoop();
    const double OriginalLength = Spline->GetSplineLength();
    TArray<FVector> OriginalSamples;
    OriginalSamples.Reserve(NumPoints * 10);
    for (int32 Sample = 0; Sample < NumPoints * 10; ++Sample)
    {
        OriginalSamples.Add(Spline->GetLocationAtSplineInputKey(Sample / 10.0, ESplineCoordinateSpace::World));
    }

    constexpr double WaterLevel = 5000.0;
    constexpr double RoadWidth = 700.0;
    constexpr double TrackWidth = 30.0;
    constexpr double TrackThickness = 4.0;
    constexpr double SegmentStep = 600.0;
    constexpr double RoadOffset = 12.0;
    constexpr double TrackCenterOffset = RoadOffset + TrackThickness * 0.5 + 2.0;
    const int32 SegmentCount = FMath::Max(1, FMath::CeilToInt(OriginalLength / SegmentStep));

    TArray<FVector> TerrainPoints;
    TerrainPoints.Reserve(SegmentCount);
    TArray<FVector> FrozenSplinePoints;
    FrozenSplinePoints.Reserve(SegmentCount);
    double MinimumTerrain = TNumericLimits<double>::Max();
    int32 WaterSamples = 0;
    for (int32 Index = 0; Index < SegmentCount; ++Index)
    {
        const FVector SplinePosition = Spline->GetLocationAtDistanceAlongSpline(OriginalLength * Index / SegmentCount, ESplineCoordinateSpace::World);
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(SplinePosition.X, SplinePosition.Y, 0.0));
        if (!Height.IsSet())
        {
            UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL refused: route sample is outside Landscape."));
            return false;
        }
        MinimumTerrain = FMath::Min(MinimumTerrain, static_cast<double>(Height.GetValue()));
        if (Height.GetValue() <= WaterLevel) ++WaterSamples;
        TerrainPoints.Add(FVector(SplinePosition.X, SplinePosition.Y, Height.GetValue()));
        FrozenSplinePoints.Add(SplinePosition);
    }

    auto Orientation = [](const FVector2D& P, const FVector2D& Q, const FVector2D& R)
    {
        const double Value = (Q.Y - P.Y) * (R.X - Q.X) - (Q.X - P.X) * (R.Y - Q.Y);
        if (FMath::IsNearlyZero(Value, 1e-6)) return 0;
        return Value > 0.0 ? 1 : 2;
    };
    auto Intersects = [&](const FVector2D& P1, const FVector2D& Q1, const FVector2D& P2, const FVector2D& Q2)
    {
        return Orientation(P1, Q1, P2) != Orientation(P1, Q1, Q2)
            && Orientation(P2, Q2, P1) != Orientation(P2, Q2, Q1);
    };
    bool bSelfIntersect = false;
    bool bLoopback = false;
    double MaxSlope = 0.0;
    for (int32 First = 0; First < TerrainPoints.Num() && !bSelfIntersect; ++First)
    {
        const int32 FirstNext = (First + 1) % TerrainPoints.Num();
        for (int32 Second = First + 2; Second < TerrainPoints.Num(); ++Second)
        {
            const int32 SecondNext = (Second + 1) % TerrainPoints.Num();
            if (First == 0 && SecondNext == 0) continue;
            if (Intersects(FVector2D(TerrainPoints[First]), FVector2D(TerrainPoints[FirstNext]),
                FVector2D(TerrainPoints[Second]), FVector2D(TerrainPoints[SecondNext])))
            {
                bSelfIntersect = true;
                break;
            }
        }
    }
    for (int32 Index = 0; Index < TerrainPoints.Num(); ++Index)
    {
        const FVector& Previous = TerrainPoints[(Index - 1 + TerrainPoints.Num()) % TerrainPoints.Num()];
        const FVector& Current = TerrainPoints[Index];
        const FVector& Next = TerrainPoints[(Index + 1) % TerrainPoints.Num()];
        const FVector& FrozenCurrent = FrozenSplinePoints[Index];
        const FVector& FrozenNext = FrozenSplinePoints[(Index + 1) % FrozenSplinePoints.Num()];
        const FVector2D Incoming(Current.X - Previous.X, Current.Y - Previous.Y);
        const FVector2D Outgoing(Next.X - Current.X, Next.Y - Current.Y);
        const double IncomingLength = Incoming.Length();
        const double OutgoingLength = Outgoing.Length();
        if (IncomingLength < 1.0 || OutgoingLength < 1.0) continue;
        const double Angle = FMath::Acos(FMath::Clamp(FVector2D::DotProduct(Incoming, Outgoing) / (IncomingLength * OutgoingLength), -1.0, 1.0));
        if (Angle > FMath::DegreesToRadians(150.0)) bLoopback = true;
        MaxSlope = FMath::Max(MaxSlope,
            FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(FrozenNext.Z - FrozenCurrent.Z), OutgoingLength)));
    }
    if (WaterSamples != 0 || bSelfIntersect || bLoopback || MaxSlope > 15.0)
    {
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL refused: frozen route validation failed. water=%d self=%s loopback=%s slope=%.2f."),
            WaterSamples, bSelfIntersect ? TEXT("YES") : TEXT("NO"), bLoopback ? TEXT("YES") : TEXT("NO"), MaxSlope);
        return false;
    }

    for (AActor* Actor : ExistingFinalActors) Actor->Destroy();
    TArray<AActor*> NewActors;
    NewActors.Reserve(SegmentCount * 2);
    int32 RoadSegments = 0;
    int32 TrackSegments = 0;
    const FName FinalFolder(TEXT("JP1993_Layout/TourRoad_Final"));
    for (int32 Index = 0; Index < TerrainPoints.Num(); ++Index)
    {
        const FVector& TerrainStart = TerrainPoints[Index];
        const FVector& TerrainEnd = TerrainPoints[(Index + 1) % TerrainPoints.Num()];
        const FVector Delta = TerrainEnd - TerrainStart;
        const double HorizontalLength = FVector2D(Delta.X, Delta.Y).Length();
        const double SegmentLength = Delta.Length();
        if (SegmentLength < 1.0 || HorizontalLength < 1.0) continue;
        const double Yaw = FMath::RadiansToDegrees(FMath::Atan2(Delta.Y, Delta.X));
        const double Pitch = FMath::RadiansToDegrees(FMath::Atan2(Delta.Z, HorizontalLength));
        const FRotator Rotation(Pitch, Yaw, 0.0);

        AStaticMeshActor* Road = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
            FTransform(Rotation, (TerrainStart + TerrainEnd) * 0.5 + FVector(0.0, 0.0, RoadOffset)));
        if (!Road) continue;
        UStaticMeshComponent* RoadMesh = Road->GetStaticMeshComponent();
        RoadMesh->SetStaticMesh(PlaneMesh);
        RoadMesh->SetWorldScale3D(FVector(SegmentLength * 1.08 / 100.0, RoadWidth / 100.0, 1.0));
        RoadMesh->SetMaterial(0, AsphaltMaterial);
        RoadMesh->SetCollisionProfileName(FName(TEXT("NoCollision")));
        RoadMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        RoadMesh->SetGenerateOverlapEvents(false);
        RoadMesh->SetCastShadow(false);
        Road->SetActorLabel(FString::Printf(TEXT("TOUR_FinalRoad_%04d"), RoadSegments));
        Road->SetFolderPath(FinalFolder);
        NewActors.Add(Road);
        ++RoadSegments;

        AStaticMeshActor* Track = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(),
            FTransform(Rotation, (TerrainStart + TerrainEnd) * 0.5 + FVector(0.0, 0.0, TrackCenterOffset)));
        if (!Track) continue;
        UStaticMeshComponent* TrackMesh = Track->GetStaticMeshComponent();
        TrackMesh->SetStaticMesh(CubeMesh);
        TrackMesh->SetWorldScale3D(FVector(SegmentLength * 1.08 / 100.0, TrackWidth / 100.0, TrackThickness / 100.0));
        TrackMesh->SetMaterial(0, TrackMaterial);
        TrackMesh->SetCollisionProfileName(FName(TEXT("NoCollision")));
        TrackMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        TrackMesh->SetGenerateOverlapEvents(false);
        TrackMesh->SetCastShadow(true);
        Track->SetActorLabel(FString::Printf(TEXT("TOUR_GuideTrack_%04d"), TrackSegments));
        Track->SetFolderPath(FinalFolder);
        NewActors.Add(Track);
        ++TrackSegments;
    }

    for (AActor* Ribbon : RibbonActors)
    {
        Ribbon->SetActorHiddenInGame(true);
        Ribbon->SetIsTemporarilyHiddenInEditor(true);
        if (USceneComponent* Root = Ribbon->GetRootComponent()) Root->SetVisibility(false, true);
    }

    bool bSplineUnchanged = Spline->GetNumberOfSplinePoints() == NumPoints
        && Spline->IsClosedLoop() == bOriginalClosedLoop
        && Spline->GetSplineLength() == OriginalLength;
    for (int32 Index = 0; Index < NumPoints && bSplineUnchanged; ++Index)
    {
        bSplineUnchanged = Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World) == OriginalPositions[Index]
            && Spline->GetArriveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World) == OriginalArriveTangents[Index]
            && Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World) == OriginalLeaveTangents[Index]
            && Spline->GetSplinePointType(Index) == OriginalPointTypes[Index];
    }
    for (int32 Sample = 0; Sample < OriginalSamples.Num() && bSplineUnchanged; ++Sample)
    {
        bSplineUnchanged = Spline->GetLocationAtSplineInputKey(Sample / 10.0, ESplineCoordinateSpace::World) == OriginalSamples[Sample];
    }

    bool bMarkersUnchanged = true;
    int32 MarkerCount = 0;
    for (FActorIterator It(World); It; ++It)
    {
        if (!It->GetActorLabel().StartsWith(TEXT("JP93_"))) continue;
        ++MarkerCount;
        const FVector* Original = MarkerPositions.Find(It->GetActorLabel());
        if (!Original || *Original != It->GetActorLocation()) bMarkersUnchanged = false;
    }
    if (!bSplineUnchanged || !bMarkersUnchanged || MarkerCount != MarkerPositions.Num()
        || RoadSegments != SegmentCount || TrackSegments != SegmentCount)
    {
        for (AActor* Actor : NewActors) Actor->Destroy();
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL failed invariants; map will not be saved. spline=%s markers=%s road=%d/%d track=%d/%d."),
            bSplineUnchanged ? TEXT("UNCHANGED") : TEXT("CHANGED"), bMarkersUnchanged ? TEXT("UNCHANGED") : TEXT("CHANGED"),
            RoadSegments, SegmentCount, TrackSegments, SegmentCount);
        return false;
    }

    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FINAL VERIFY ROAD_WIDTH=%.0f cm TRACK_WIDTH=%.0f cm TRACK_THICKNESS=%.0f cm ROAD_SEGMENTS=%d TRACK_SEGMENTS=%d ROUTE_LENGTH=%.1f cm (%.3f km) MIN_TERRAIN=%.1f WATER_SAMPLES=%d SELF_INTERSECT=%s LOOPBACK=%s MAX_SLOPE=%.2f SPLINE_BYTE_GEOMETRY_UNCHANGED=%s RIBBON_HIDDEN=%d"),
        RoadWidth, TrackWidth, TrackThickness, RoadSegments, TrackSegments, OriginalLength, OriginalLength / 100000.0,
        MinimumTerrain, WaterSamples, bSelfIntersect ? TEXT("YES") : TEXT("NO"), bLoopback ? TEXT("YES") : TEXT("NO"),
        MaxSlope, bSplineUnchanged ? TEXT("YES") : TEXT("NO"), RibbonActors.Num());

    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        UE_LOG(LogTemp, Error, TEXT("JPTOUR_FINAL failed to save target map."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JPTOUR_FINAL SUCCESS: asphalt road and Explorer guide track saved."));
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::ProbeTourRoadGrading()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING_PROBE refused: editor is unavailable."));
        return false;
    }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING_PROBE refused: target test map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    USplineComponent* Spline = nullptr;
    TArray<AStaticMeshActor*> RoadActors;
    TMap<FString, FVector> MarkerPositions;
    for (FActorIterator It(World); It; ++It)
    {
        const FString Label = It->GetActorLabel();
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It)) Landscape = Proxy;
        if (Label == TEXT("TOUR_RoadGuide")) Spline = It->FindComponentByClass<USplineComponent>();
        if (Label.StartsWith(TEXT("TOUR_FinalRoad_")))
        {
            if (AStaticMeshActor* Road = Cast<AStaticMeshActor>(*It)) RoadActors.Add(Road);
        }
        if (Label.StartsWith(TEXT("JP93_"))) MarkerPositions.Add(Label, It->GetActorLocation());
    }
    if (!Landscape || !Spline || RoadActors.Num() == 0 || MarkerPositions.Num() != 10)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING_PROBE refused: Landscape, frozen guide, road actors, or markers are missing."));
        return false;
    }
    RoadActors.Sort([](const AStaticMeshActor& A, const AStaticMeshActor& B)
    {
        return A.GetActorLabel() < B.GetActorLabel();
    });

    ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
    FIntRect Extent;
    if (!LandscapeInfo || !LandscapeInfo->GetLandscapeExtent(Landscape, Extent))
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING_PROBE refused: Landscape extent is unavailable."));
        return false;
    }
    const int32 Width = Extent.Width() + 1;
    const int32 Height = Extent.Height() + 1;
    TArray<uint16> RawHeights;
    RawHeights.SetNumUninitialized(Width * Height);
    FLandscapeEditDataInterface Edit(LandscapeInfo, false);
    Edit.GetHeightDataFast(Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y, RawHeights.GetData(), Width);

    const FTransform LandscapeTransform = Landscape->LandscapeActorToWorld();
    double MinimumWorldHeight = TNumericLimits<double>::Max();
    double MaximumWorldHeight = -TNumericLimits<double>::Max();
    long double HeightSum = 0.0;
    for (int32 Y = Extent.Min.Y; Y <= Extent.Max.Y; ++Y)
    {
        for (int32 X = Extent.Min.X; X <= Extent.Max.X; ++X)
        {
            const uint16 RawHeight = RawHeights[(Y - Extent.Min.Y) * Width + X - Extent.Min.X];
            const double WorldHeight = LandscapeTransform.TransformPosition(
                FVector(X, Y, LandscapeDataAccess::GetLocalHeight(RawHeight))).Z;
            MinimumWorldHeight = FMath::Min(MinimumWorldHeight, WorldHeight);
            MaximumWorldHeight = FMath::Max(MaximumWorldHeight, WorldHeight);
            HeightSum += WorldHeight;
        }
    }
    const double MeanWorldHeight = static_cast<double>(HeightSum / RawHeights.Num());
    const uint32 HeightCrc = FCrc::MemCrc32(RawHeights.GetData(), RawHeights.Num() * sizeof(uint16));

    struct FProposedVertex
    {
        double Distance = TNumericLimits<double>::Max();
        double RoadSurfaceZ = 0.0;
    };
    TMap<FIntPoint, FProposedVertex> ProposedVertices;
    constexpr double CoreHalfWidth = 450.0;
    constexpr double OuterHalfWidth = 1100.0;
    const double LocalRadius = OuterHalfWidth / FMath::Min(FMath::Abs(LandscapeTransform.GetScale3D().X), FMath::Abs(LandscapeTransform.GetScale3D().Y));

    for (AStaticMeshActor* Road : RoadActors)
    {
        UStaticMeshComponent* Mesh = Road->GetStaticMeshComponent();
        if (!Mesh) continue;
        const double CenterlineLength = Mesh->GetComponentScale().X * 100.0 / 1.08;
        const FVector Forward = Road->GetActorForwardVector();
        const FVector SegmentStart = Road->GetActorLocation() - Forward * CenterlineLength * 0.5;
        const FVector SegmentEnd = Road->GetActorLocation() + Forward * CenterlineLength * 0.5;
        const FVector StartLocal = LandscapeTransform.InverseTransformPosition(SegmentStart);
        const FVector EndLocal = LandscapeTransform.InverseTransformPosition(SegmentEnd);
        const int32 MinX = FMath::Clamp(FMath::FloorToInt(FMath::Min(StartLocal.X, EndLocal.X) - LocalRadius - 1.0), Extent.Min.X, Extent.Max.X);
        const int32 MaxX = FMath::Clamp(FMath::CeilToInt(FMath::Max(StartLocal.X, EndLocal.X) + LocalRadius + 1.0), Extent.Min.X, Extent.Max.X);
        const int32 MinY = FMath::Clamp(FMath::FloorToInt(FMath::Min(StartLocal.Y, EndLocal.Y) - LocalRadius - 1.0), Extent.Min.Y, Extent.Max.Y);
        const int32 MaxY = FMath::Clamp(FMath::CeilToInt(FMath::Max(StartLocal.Y, EndLocal.Y) + LocalRadius + 1.0), Extent.Min.Y, Extent.Max.Y);
        const FVector2D A(SegmentStart.X, SegmentStart.Y);
        const FVector2D B(SegmentEnd.X, SegmentEnd.Y);
        const FVector2D AB = B - A;
        const double LengthSquared = AB.SquaredLength();
        if (LengthSquared < 1.0) continue;

        for (int32 Y = MinY; Y <= MaxY; ++Y)
        {
            for (int32 X = MinX; X <= MaxX; ++X)
            {
                const FVector WorldVertex = LandscapeTransform.TransformPosition(FVector(X, Y, 0.0));
                const FVector2D P(WorldVertex.X, WorldVertex.Y);
                const double T = FMath::Clamp(FVector2D::DotProduct(P - A, AB) / LengthSquared, 0.0, 1.0);
                const FVector2D Closest = A + AB * T;
                const double Distance = FVector2D::Distance(P, Closest);
                if (Distance > OuterHalfWidth) continue;
                FProposedVertex* Existing = ProposedVertices.Find(FIntPoint(X, Y));
                if (!Existing || Distance < Existing->Distance)
                {
                    ProposedVertices.Add(FIntPoint(X, Y), {Distance, FMath::Lerp(SegmentStart.Z, SegmentEnd.Z, T)});
                }
            }
        }
    }

    double MinimumDelta = TNumericLimits<double>::Max();
    double MaximumDelta = -TNumericLimits<double>::Max();
    double MinimumOriginalCorridorHeight = TNumericLimits<double>::Max();
    double MaximumOriginalCorridorHeight = -TNumericLimits<double>::Max();
    int32 CoreVertices = 0;
    int32 ChangedVertices = 0;
    FIntRect CorridorBounds(FIntPoint(MAX_int32, MAX_int32), FIntPoint(MIN_int32, MIN_int32));
    for (const TPair<FIntPoint, FProposedVertex>& Pair : ProposedVertices)
    {
        const int32 RawIndex = (Pair.Key.Y - Extent.Min.Y) * Width + Pair.Key.X - Extent.Min.X;
        const double OriginalWorldZ = LandscapeTransform.TransformPosition(
            FVector(Pair.Key.X, Pair.Key.Y, LandscapeDataAccess::GetLocalHeight(RawHeights[RawIndex]))).Z;
        MinimumOriginalCorridorHeight = FMath::Min(MinimumOriginalCorridorHeight, OriginalWorldZ);
        MaximumOriginalCorridorHeight = FMath::Max(MaximumOriginalCorridorHeight, OriginalWorldZ);
        const double Alpha = Pair.Value.Distance <= CoreHalfWidth
            ? 1.0
            : 1.0 - FMath::SmoothStep(CoreHalfWidth, OuterHalfWidth, Pair.Value.Distance);
        const double TargetWorldZ = FMath::Max(5300.0, Pair.Value.RoadSurfaceZ - 15.0);
        const double Delta = FMath::Lerp(OriginalWorldZ, TargetWorldZ, Alpha) - OriginalWorldZ;
        MinimumDelta = FMath::Min(MinimumDelta, Delta);
        MaximumDelta = FMath::Max(MaximumDelta, Delta);
        if (Pair.Value.Distance <= CoreHalfWidth) ++CoreVertices;
        if (FMath::Abs(Delta) >= 0.5) ++ChangedVertices;
        CorridorBounds.Min.X = FMath::Min(CorridorBounds.Min.X, Pair.Key.X);
        CorridorBounds.Min.Y = FMath::Min(CorridorBounds.Min.Y, Pair.Key.Y);
        CorridorBounds.Max.X = FMath::Max(CorridorBounds.Max.X, Pair.Key.X);
        CorridorBounds.Max.Y = FMath::Max(CorridorBounds.Max.Y, Pair.Key.Y);
    }

    UE_LOG(LogTemp, Display, TEXT("JPGRADING_PROBE METHOD=FLandscapeEditDataInterface LOCAL_RAW_VERTEX_EDIT RENDER_TARGETS=NO HEIGHTMAP_EXPORT_IMPORT=NO IN_MEMORY_ROLLBACK=YES"));
    UE_LOG(LogTemp, Display, TEXT("JPGRADING_PROBE LANDSCAPE_TRANSFORM LOCATION=(%.6f,%.6f,%.6f) ROTATION=(%.6f,%.6f,%.6f) SCALE=(%.6f,%.6f,%.6f) EXTENT=(%d,%d)-(%d,%d) VERTICES=%d"),
        LandscapeTransform.GetLocation().X, LandscapeTransform.GetLocation().Y, LandscapeTransform.GetLocation().Z,
        LandscapeTransform.Rotator().Pitch, LandscapeTransform.Rotator().Yaw, LandscapeTransform.Rotator().Roll,
        LandscapeTransform.GetScale3D().X, LandscapeTransform.GetScale3D().Y, LandscapeTransform.GetScale3D().Z,
        Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y, RawHeights.Num());
    UE_LOG(LogTemp, Display, TEXT("JPGRADING_PROBE HEIGHT_STATS MIN=%.3f MAX=%.3f MEAN=%.3f RAW_CRC32=%08X"),
        MinimumWorldHeight, MaximumWorldHeight, MeanWorldHeight, HeightCrc);
    UE_LOG(LogTemp, Display, TEXT("JPGRADING_PROBE PROPOSAL ROAD_WIDTH=700 CORE_WIDTH=900 TOTAL_WIDTH=2200 TARGET_GAP=15 CORRIDOR_VERTICES=%d CORE_VERTICES=%d CHANGED_VERTICES=%d LOCAL_BOUNDS=(%d,%d)-(%d,%d) ORIGINAL_CORRIDOR_MIN=%.3f MAX=%.3f CUT_MAX=%.3f FILL_MAX=%.3f ROAD_ACTORS=%d SPLINE_POINTS=%d ROUTE_LENGTH=%.1f MARKERS=%d"),
        ProposedVertices.Num(), CoreVertices, ChangedVertices,
        CorridorBounds.Min.X, CorridorBounds.Min.Y, CorridorBounds.Max.X, CorridorBounds.Max.Y,
        MinimumOriginalCorridorHeight, MaximumOriginalCorridorHeight, MinimumDelta, MaximumDelta,
        RoadActors.Num(), Spline->GetNumberOfSplinePoints(), Spline->GetSplineLength(), MarkerPositions.Num());
    return ProposedVertices.Num() > 0;
}

bool UJPJurassicDreamLandscapeImportLibrary::GradeTourRoadLandscape()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING refused: editor is unavailable."));
        return false;
    }
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING refused: only the target test map may be active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    USplineComponent* Spline = nullptr;
    TArray<AStaticMeshActor*> RoadActors;
    TMap<FString, FVector> MarkerPositions;
    for (FActorIterator It(World); It; ++It)
    {
        const FString Label = It->GetActorLabel();
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It)) Landscape = Proxy;
        if (Label == TEXT("TOUR_RoadGuide")) Spline = It->FindComponentByClass<USplineComponent>();
        if (Label.StartsWith(TEXT("TOUR_FinalRoad_")))
        {
            if (AStaticMeshActor* Road = Cast<AStaticMeshActor>(*It)) RoadActors.Add(Road);
        }
        if (Label.StartsWith(TEXT("JP93_"))) MarkerPositions.Add(Label, It->GetActorLocation());
    }
    if (!Landscape || !Spline || Spline->GetNumberOfSplinePoints() != 14 || RoadActors.Num() != 988 || MarkerPositions.Num() != 10)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING refused: frozen road invariants are missing."));
        return false;
    }
    RoadActors.Sort([](const AStaticMeshActor& A, const AStaticMeshActor& B)
    {
        return A.GetActorLabel() < B.GetActorLabel();
    });

    const FTransform OriginalLandscapeTransform = Landscape->GetActorTransform();
    TMap<FString, FTransform> OriginalRoadTransforms;
    for (AStaticMeshActor* Road : RoadActors) OriginalRoadTransforms.Add(Road->GetActorLabel(), Road->GetActorTransform());
    const int32 NumPoints = Spline->GetNumberOfSplinePoints();
    TArray<FVector> OriginalPositions;
    TArray<FVector> OriginalArriveTangents;
    TArray<FVector> OriginalLeaveTangents;
    TArray<ESplinePointType::Type> OriginalPointTypes;
    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        OriginalPositions.Add(Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalArriveTangents.Add(Spline->GetArriveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalLeaveTangents.Add(Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World));
        OriginalPointTypes.Add(Spline->GetSplinePointType(Index));
    }
    const bool bOriginalClosedLoop = Spline->IsClosedLoop();
    const double OriginalSplineLength = Spline->GetSplineLength();

    ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
    FIntRect Extent;
    if (!LandscapeInfo || !LandscapeInfo->SupportsLandscapeEditing()
        || !LandscapeInfo->IsLandscapeEditableWorld()
        || !LandscapeInfo->GetLandscapeExtent(Landscape, Extent))
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING refused: Landscape does not expose safe local editing in this world."));
        return false;
    }
    const int32 Width = Extent.Width() + 1;
    const int32 Height = Extent.Height() + 1;
    TArray<uint16> OriginalRawHeights;
    OriginalRawHeights.SetNumUninitialized(Width * Height);
    {
        FLandscapeEditDataInterface ReadEdit(LandscapeInfo);
        ReadEdit.GetHeightDataFast(Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y, OriginalRawHeights.GetData(), Width);
    }
    const uint32 OriginalHeightCrc = FCrc::MemCrc32(OriginalRawHeights.GetData(), OriginalRawHeights.Num() * sizeof(uint16));
    const FTransform LandscapeTransform = Landscape->LandscapeActorToWorld();

    struct FGradeVertex
    {
        double Distance = TNumericLimits<double>::Max();
        double RoadSurfaceZ = 0.0;
    };
    TMap<FIntPoint, FGradeVertex> CorridorVertices;
    constexpr double CoreHalfWidth = 450.0;
    constexpr double OuterHalfWidth = 1100.0;
    constexpr double TargetGap = 15.0;
    constexpr double MinimumDryHeight = 5000.0;
    const double LocalRadius = OuterHalfWidth / FMath::Min(FMath::Abs(LandscapeTransform.GetScale3D().X), FMath::Abs(LandscapeTransform.GetScale3D().Y));

    for (AStaticMeshActor* Road : RoadActors)
    {
        UStaticMeshComponent* Mesh = Road->GetStaticMeshComponent();
        if (!Mesh) continue;
        const double CenterlineLength = Mesh->GetComponentScale().X * 100.0 / 1.08;
        const FVector Forward = Road->GetActorForwardVector();
        const FVector SegmentStart = Road->GetActorLocation() - Forward * CenterlineLength * 0.5;
        const FVector SegmentEnd = Road->GetActorLocation() + Forward * CenterlineLength * 0.5;
        const FVector StartLocal = LandscapeTransform.InverseTransformPosition(SegmentStart);
        const FVector EndLocal = LandscapeTransform.InverseTransformPosition(SegmentEnd);
        const int32 MinX = FMath::Clamp(FMath::FloorToInt(FMath::Min(StartLocal.X, EndLocal.X) - LocalRadius - 1.0), Extent.Min.X, Extent.Max.X);
        const int32 MaxX = FMath::Clamp(FMath::CeilToInt(FMath::Max(StartLocal.X, EndLocal.X) + LocalRadius + 1.0), Extent.Min.X, Extent.Max.X);
        const int32 MinY = FMath::Clamp(FMath::FloorToInt(FMath::Min(StartLocal.Y, EndLocal.Y) - LocalRadius - 1.0), Extent.Min.Y, Extent.Max.Y);
        const int32 MaxY = FMath::Clamp(FMath::CeilToInt(FMath::Max(StartLocal.Y, EndLocal.Y) + LocalRadius + 1.0), Extent.Min.Y, Extent.Max.Y);
        const FVector2D A(SegmentStart.X, SegmentStart.Y);
        const FVector2D B(SegmentEnd.X, SegmentEnd.Y);
        const FVector2D AB = B - A;
        const double LengthSquared = AB.SquaredLength();
        if (LengthSquared < 1.0) continue;
        for (int32 Y = MinY; Y <= MaxY; ++Y)
        {
            for (int32 X = MinX; X <= MaxX; ++X)
            {
                const FVector WorldVertex = LandscapeTransform.TransformPosition(FVector(X, Y, 0.0));
                const FVector2D P(WorldVertex.X, WorldVertex.Y);
                const double T = FMath::Clamp(FVector2D::DotProduct(P - A, AB) / LengthSquared, 0.0, 1.0);
                const double Distance = FVector2D::Distance(P, A + AB * T);
                if (Distance > OuterHalfWidth) continue;
                FGradeVertex* Existing = CorridorVertices.Find(FIntPoint(X, Y));
                if (!Existing || Distance < Existing->Distance)
                {
                    CorridorVertices.Add(FIntPoint(X, Y), {Distance, FMath::Lerp(SegmentStart.Z, SegmentEnd.Z, T)});
                }
            }
        }
    }

    TArray<uint16> ProposedRawHeights = OriginalRawHeights;
    TSet<FIntPoint> ChangedVertices;
    TSet<FIntPoint> ChangedTiles;
    constexpr int32 TileSize = 255;
    double MinimumDelta = TNumericLimits<double>::Max();
    double MaximumDelta = -TNumericLimits<double>::Max();
    int32 SkippedWaterVertices = 0;
    for (const TPair<FIntPoint, FGradeVertex>& Pair : CorridorVertices)
    {
        const int32 RawIndex = (Pair.Key.Y - Extent.Min.Y) * Width + Pair.Key.X - Extent.Min.X;
        const double OriginalWorldZ = LandscapeTransform.TransformPosition(
            FVector(Pair.Key.X, Pair.Key.Y, LandscapeDataAccess::GetLocalHeight(OriginalRawHeights[RawIndex]))).Z;
        if (OriginalWorldZ <= MinimumDryHeight)
        {
            ++SkippedWaterVertices;
            continue;
        }
        const double Alpha = Pair.Value.Distance <= CoreHalfWidth
            ? 1.0
            : 1.0 - FMath::SmoothStep(CoreHalfWidth, OuterHalfWidth, Pair.Value.Distance);
        const double TargetWorldZ = FMath::Max(5300.0, Pair.Value.RoadSurfaceZ - TargetGap);
        const double DesiredWorldZ = FMath::Lerp(OriginalWorldZ, TargetWorldZ, Alpha);
        const FVector WorldVertex = LandscapeTransform.TransformPosition(FVector(Pair.Key.X, Pair.Key.Y, 0.0));
        const double DesiredLocalZ = LandscapeTransform.InverseTransformPosition(FVector(WorldVertex.X, WorldVertex.Y, DesiredWorldZ)).Z;
        const uint16 ProposedRaw = LandscapeDataAccess::GetTexHeight(DesiredLocalZ);
        if (ProposedRaw == OriginalRawHeights[RawIndex]) continue;
        ProposedRawHeights[RawIndex] = ProposedRaw;
        ChangedVertices.Add(Pair.Key);
        ChangedTiles.Add(FIntPoint((Pair.Key.X - Extent.Min.X) / TileSize, (Pair.Key.Y - Extent.Min.Y) / TileSize));
        const double QuantizedWorldZ = LandscapeTransform.TransformPosition(
            FVector(Pair.Key.X, Pair.Key.Y, LandscapeDataAccess::GetLocalHeight(ProposedRaw))).Z;
        MinimumDelta = FMath::Min(MinimumDelta, QuantizedWorldZ - OriginalWorldZ);
        MaximumDelta = FMath::Max(MaximumDelta, QuantizedWorldZ - OriginalWorldZ);
    }
    if (ChangedVertices.Num() == 0 || ChangedTiles.Num() == 0)
    {
        UE_LOG(LogTemp, Error, TEXT("JPGRADING refused: proposal produced no local height changes."));
        return false;
    }

    auto WriteTiles = [&](const TArray<uint16>& SourceHeights)
    {
        FLandscapeEditDataInterface Edit(LandscapeInfo);
        for (const FIntPoint& Tile : ChangedTiles)
        {
            const int32 MinX = Extent.Min.X + Tile.X * TileSize;
            const int32 MinY = Extent.Min.Y + Tile.Y * TileSize;
            const int32 MaxX = FMath::Min(MinX + TileSize, Extent.Max.X);
            const int32 MaxY = FMath::Min(MinY + TileSize, Extent.Max.Y);
            const int32 PatchWidth = MaxX - MinX + 1;
            const int32 PatchHeight = MaxY - MinY + 1;
            TArray<uint16> Patch;
            Patch.SetNumUninitialized(PatchWidth * PatchHeight);
            for (int32 Y = MinY; Y <= MaxY; ++Y)
            {
                FMemory::Memcpy(Patch.GetData() + (Y - MinY) * PatchWidth,
                    SourceHeights.GetData() + (Y - Extent.Min.Y) * Width + MinX - Extent.Min.X,
                    PatchWidth * sizeof(uint16));
            }
            Edit.SetHeightData(MinX, MinY, MaxX, MaxY, Patch.GetData(), PatchWidth, true);
        }
        Edit.Flush();
    };

    Landscape->Modify();
    WriteTiles(ProposedRawHeights);
    {
        int32 FlushedComponents = 0;
        LandscapeInfo->ForAllLandscapeComponents([&](ULandscapeComponent* Component)
        {
            if (!Component) return;
            const FIntPoint Key = Component->GetComponentKey();
            if (!ChangedTiles.Contains(FIntPoint(Key.X, Key.Y))) return;
            Component->UpdateCollisionData(/*bInUpdateHeightfieldRegion=*/true);
            LandscapeInfo->MarkObjectDirty(Component);
            ++FlushedComponents;
        });
        FlushRenderingCommands();
        UE_LOG(LogTemp, Display, TEXT("JPGRADING COLLISION_FLUSH COMPONENTS=%d TILES=%d"), FlushedComponents, ChangedTiles.Num());
    }

    auto Rollback = [&]()
    {
        WriteTiles(OriginalRawHeights);
        UE_LOG(LogTemp, Warning, TEXT("JPGRADING rollback completed through FLandscapeEditDataInterface; no map save performed."));
    };

    TArray<uint16> VerifiedRawHeights;
    VerifiedRawHeights.SetNumUninitialized(OriginalRawHeights.Num());
    {
        FLandscapeEditDataInterface VerifyEdit(LandscapeInfo);
        VerifyEdit.GetHeightDataFast(Extent.Min.X, Extent.Min.Y, Extent.Max.X, Extent.Max.Y, VerifiedRawHeights.GetData(), Width);
    }
    int32 ActualChangedVertices = 0;
    int32 UnexpectedChangedVertices = 0;
    for (int32 Index = 0; Index < VerifiedRawHeights.Num(); ++Index)
    {
        if (VerifiedRawHeights[Index] == OriginalRawHeights[Index]) continue;
        ++ActualChangedVertices;
        const int32 X = Extent.Min.X + Index % Width;
        const int32 Y = Extent.Min.Y + Index / Width;
        if (!ChangedVertices.Contains(FIntPoint(X, Y)) || VerifiedRawHeights[Index] != ProposedRawHeights[Index])
        {
            ++UnexpectedChangedVertices;
        }
    }

    auto SampleGradedWorldZ = [&](double WorldX, double WorldY, double& OutZ) -> bool
    {
        const FVector Local = LandscapeTransform.InverseTransformPosition(FVector(WorldX, WorldY, 0.0));
        const int32 X0 = FMath::FloorToInt(Local.X);
        const int32 Y0 = FMath::FloorToInt(Local.Y);
        if (X0 < Extent.Min.X || Y0 < Extent.Min.Y || X0 + 1 > Extent.Max.X || Y0 + 1 > Extent.Max.Y) return false;
        const double TX = Local.X - X0;
        const double TY = Local.Y - Y0;
        auto VertexWorldZ = [&](int32 X, int32 Y)
        {
            const uint16 Raw = VerifiedRawHeights[(Y - Extent.Min.Y) * Width + X - Extent.Min.X];
            return LandscapeTransform.TransformPosition(FVector(X, Y, LandscapeDataAccess::GetLocalHeight(Raw))).Z;
        };
        OutZ = FMath::Lerp(
            FMath::Lerp(VertexWorldZ(X0, Y0), VertexWorldZ(X0 + 1, Y0), TX),
            FMath::Lerp(VertexWorldZ(X0, Y0 + 1), VertexWorldZ(X0 + 1, Y0 + 1), TX), TY);
        return true;
    };

    double MinimumGap = TNumericLimits<double>::Max();
    double MaximumGap = -TNumericLimits<double>::Max();
    double MinimumCenterlineTerrain = TNumericLimits<double>::Max();
    int32 CenterlineWaterSamples = 0;
    FString MinimumGapActor;
    FString MaximumGapActor;
    for (AStaticMeshActor* Road : RoadActors)
    {
        const FVector RoadCenter = Road->GetActorLocation();
        double TerrainZ = 0.0;
        if (!SampleGradedWorldZ(RoadCenter.X, RoadCenter.Y, TerrainZ))
        {
            ++CenterlineWaterSamples;
            continue;
        }
        MinimumCenterlineTerrain = FMath::Min(MinimumCenterlineTerrain, TerrainZ);
        if (TerrainZ <= MinimumDryHeight) ++CenterlineWaterSamples;
        const double Gap = RoadCenter.Z - TerrainZ;
        if (Gap < MinimumGap)
        {
            MinimumGap = Gap;
            MinimumGapActor = Road->GetActorLabel();
        }
        if (Gap > MaximumGap)
        {
            MaximumGap = Gap;
            MaximumGapActor = Road->GetActorLabel();
        }
    }

    bool bSplineUnchanged = Spline->GetNumberOfSplinePoints() == NumPoints
        && Spline->IsClosedLoop() == bOriginalClosedLoop
        && Spline->GetSplineLength() == OriginalSplineLength;
    for (int32 Index = 0; Index < NumPoints && bSplineUnchanged; ++Index)
    {
        bSplineUnchanged = Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World) == OriginalPositions[Index]
            && Spline->GetArriveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World) == OriginalArriveTangents[Index]
            && Spline->GetLeaveTangentAtSplinePoint(Index, ESplineCoordinateSpace::World) == OriginalLeaveTangents[Index]
            && Spline->GetSplinePointType(Index) == OriginalPointTypes[Index];
    }
    bool bMarkersUnchanged = true;
    int32 MarkerCount = 0;
    for (FActorIterator It(World); It; ++It)
    {
        if (!It->GetActorLabel().StartsWith(TEXT("JP93_"))) continue;
        ++MarkerCount;
        const FVector* Original = MarkerPositions.Find(It->GetActorLabel());
        if (!Original || *Original != It->GetActorLocation()) bMarkersUnchanged = false;
    }
    bool bRoadUnchanged = true;
    for (AStaticMeshActor* Road : RoadActors)
    {
        const FTransform* Original = OriginalRoadTransforms.Find(Road->GetActorLabel());
        if (!Original || !Road->GetActorTransform().Equals(*Original, 0.0)) bRoadUnchanged = false;
    }

    constexpr double ValidationStep = 600.0;
    const int32 RouteSteps = FMath::Max(3, FMath::CeilToInt(OriginalSplineLength / ValidationStep));
    TArray<FVector> RouteSamples;
    RouteSamples.Reserve(RouteSteps);
    for (int32 Step = 0; Step < RouteSteps; ++Step)
    {
        RouteSamples.Add(Spline->GetLocationAtDistanceAlongSpline(OriginalSplineLength * Step / RouteSteps, ESplineCoordinateSpace::World));
    }
    double MaxSlope = 0.0;
    for (int32 Index = 0; Index < RouteSamples.Num(); ++Index)
    {
        const FVector& Current = RouteSamples[Index];
        const FVector& Next = RouteSamples[(Index + 1) % RouteSamples.Num()];
        const double Horizontal = FVector2D::Distance(FVector2D(Current), FVector2D(Next));
        if (Horizontal > 1.0)
        {
            MaxSlope = FMath::Max(MaxSlope,
                FMath::RadiansToDegrees(FMath::Atan2(FMath::Abs(Next.Z - Current.Z), Horizontal)));
        }
    }

    const bool bLandscapeTransformUnchanged = Landscape->GetActorTransform().Equals(OriginalLandscapeTransform, 0.0);
    const bool bGapValid = MinimumGap >= 8.0 && MaximumGap <= 22.0;
    const bool bValid = UnexpectedChangedVertices == 0
        && ActualChangedVertices == ChangedVertices.Num()
        && CenterlineWaterSamples == 0
        && MinimumCenterlineTerrain > MinimumDryHeight
        && bGapValid && MaxSlope <= 15.0
        && bSplineUnchanged && bMarkersUnchanged && MarkerCount == MarkerPositions.Num()
        && bRoadUnchanged && bLandscapeTransformUnchanged;

    UE_LOG(LogTemp, Display, TEXT("JPGRADING VERIFY METHOD=LOCAL_RAW_VERTEX_EDIT RENDER_TARGETS=NO HEIGHTMAP_EXPORT_IMPORT=NO ORIGINAL_CRC32=%08X CHANGED_VERTICES=%d ACTUAL_CHANGED=%d UNEXPECTED_CHANGED=%d TILES=%d SKIPPED_WATER_VERTICES=%d CUT_MAX=%.3f FILL_MAX=%.3f MIN_GAP=%.3f MAX_GAP=%.3f MIN_CENTERLINE_TERRAIN=%.3f WATER_SAMPLES=%d MAX_ROUTE_SLOPE=%.3f SPLINE_UNCHANGED=%s MARKERS_UNCHANGED=%s ROAD_UNCHANGED=%s TRANSFORM_UNCHANGED=%s"),
        OriginalHeightCrc, ChangedVertices.Num(), ActualChangedVertices, UnexpectedChangedVertices,
        ChangedTiles.Num(), SkippedWaterVertices, MinimumDelta, MaximumDelta,
        MinimumGap, MaximumGap, MinimumCenterlineTerrain, CenterlineWaterSamples, MaxSlope,
        bSplineUnchanged ? TEXT("YES") : TEXT("NO"), bMarkersUnchanged ? TEXT("YES") : TEXT("NO"),
        bRoadUnchanged ? TEXT("YES") : TEXT("NO"), bLandscapeTransformUnchanged ? TEXT("YES") : TEXT("NO"));
    UE_LOG(LogTemp, Display, TEXT("JPGRADING CLEARANCE_DIAGNOSTIC SOURCE=VERIFIED_RAW_HEIGHTFIELD_BILINEAR MIN_ACTOR=%s MAX_ACTOR=%s COLLISION_ASYNC_STALENESS_AVOIDED=YES"),
        *MinimumGapActor, *MaximumGapActor);
    if (!bValid)
    {
        Rollback();
        UE_LOG(LogTemp, Error, TEXT("JPGRADING failed validation; Landscape restored and map not saved."));
        return false;
    }

    Landscape->MarkPackageDirty();
    if (!FEditorFileUtils::SaveLevel(World->PersistentLevel))
    {
        Rollback();
        UE_LOG(LogTemp, Error, TEXT("JPGRADING failed to save target test map; Landscape restored in memory."));
        return false;
    }
    UE_LOG(LogTemp, Display, TEXT("JPGRADING SUCCESS: local roadbed grading saved only to target test map."));
    return true;
}

bool UJPJurassicDreamLandscapeImportLibrary::ProbeTourRoadWaterCrossing()
{
    if (!GEditor)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_PROBE refused: editor is unavailable."));
        return false;
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World || !World->PersistentLevel || World->GetOutermost()->GetName() != TargetMapPackage)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_PROBE refused: target map is not active."));
        return false;
    }

    ALandscapeProxy* Landscape = nullptr;
    USplineComponent* Spline = nullptr;
    for (FActorIterator It(World); It; ++It)
    {
        if (ALandscapeProxy* Proxy = Cast<ALandscapeProxy>(*It)) Landscape = Proxy;
        if (It->GetActorLabel() == TEXT("TOUR_RoadGuide")) Spline = It->FindComponentByClass<USplineComponent>();
    }
    if (!Landscape || !Spline)
    {
        UE_LOG(LogTemp, Error, TEXT("JPWATER_PROBE refused: Landscape or TOUR_RoadGuide is missing."));
        return false;
    }

    constexpr double WaterLevel = 5000.0;
    constexpr int32 SamplesPerSegment = 100;
    const int32 NumPoints = Spline->GetNumberOfSplinePoints();
    bool bInWater = false;
    double IntervalStartKey = 0.0;
    FVector IntervalStart = FVector::ZeroVector;
    double IntervalMinHeight = TNumericLimits<double>::Max();
    int32 IntervalCount = 0;
    int32 WaterSamples = 0;
    double GlobalMinHeight = TNumericLimits<double>::Max();

    for (int32 Sample = 0; Sample <= NumPoints * SamplesPerSegment; ++Sample)
    {
        const double InputKey = static_cast<double>(Sample) / SamplesPerSegment;
        const FVector Position = Spline->GetLocationAtSplineInputKey(InputKey, ESplineCoordinateSpace::World);
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Position.X, Position.Y, 0.0));
        if (!Height.IsSet())
        {
            UE_LOG(LogTemp, Error, TEXT("JPWATER_PROBE failed: spline sample %.2f is outside the Landscape."), InputKey);
            return false;
        }

        const double TerrainHeight = Height.GetValue();
        GlobalMinHeight = FMath::Min(GlobalMinHeight, TerrainHeight);
        const bool bWater = TerrainHeight <= WaterLevel;
        if (bWater)
        {
            ++WaterSamples;
            if (!bInWater)
            {
                bInWater = true;
                IntervalStartKey = InputKey;
                IntervalStart = Position;
                IntervalMinHeight = TerrainHeight;
            }
            IntervalMinHeight = FMath::Min(IntervalMinHeight, TerrainHeight);
        }
        else if (bInWater)
        {
            ++IntervalCount;
            UE_LOG(LogTemp, Display, TEXT("JPWATER_PROBE INTERVAL=%d START_KEY=%.2f END_KEY=%.2f START=(%.0f,%.0f) END=(%.0f,%.0f) MIN_HEIGHT=%.1f CLEARANCE=%.1f"),
                IntervalCount, IntervalStartKey, InputKey - 1.0 / SamplesPerSegment,
                IntervalStart.X, IntervalStart.Y, Position.X, Position.Y,
                IntervalMinHeight, IntervalMinHeight - WaterLevel);
            bInWater = false;
        }
    }
    if (bInWater)
    {
        ++IntervalCount;
        UE_LOG(LogTemp, Display, TEXT("JPWATER_PROBE INTERVAL=%d START_KEY=%.2f END_KEY=%.2f START=(%.0f,%.0f) MIN_HEIGHT=%.1f CLEARANCE=%.1f"),
            IntervalCount, IntervalStartKey, static_cast<double>(NumPoints),
            IntervalStart.X, IntervalStart.Y, IntervalMinHeight, IntervalMinHeight - WaterLevel);
    }

    for (int32 Index = 0; Index < NumPoints; ++Index)
    {
        const FVector Position = Spline->GetLocationAtSplinePoint(Index, ESplineCoordinateSpace::World);
        const TOptional<float> Height = Landscape->GetHeightAtLocation(FVector(Position.X, Position.Y, 0.0));
        UE_LOG(LogTemp, Display, TEXT("JPWATER_PROBE CONTROL=%d POS=(%.0f,%.0f,%.0f) TERRAIN=%.1f"),
            Index, Position.X, Position.Y, Position.Z, Height.IsSet() ? Height.GetValue() : -1.0f);
    }

    double FreshMinimumGap = TNumericLimits<double>::Max();
    double FreshMaximumGap = -TNumericLimits<double>::Max();
    int32 FreshGapSamples = 0;
    int32 FreshWaterSamples = 0;
    FString FreshMinimumActor;
    FString FreshMaximumActor;

    ULandscapeInfo* ProbeInfo = Landscape->GetLandscapeInfo();
    FIntRect ProbeExtent;
    TArray<uint16> ProbeRaw;
    int32 ProbeWidth = 0;
    const bool bHaveRaw = ProbeInfo && ProbeInfo->GetLandscapeExtent(Landscape, ProbeExtent);
    if (bHaveRaw)
    {
        ProbeWidth = ProbeExtent.Width() + 1;
        ProbeRaw.SetNumUninitialized(ProbeWidth * (ProbeExtent.Height() + 1));
        {
            FLandscapeEditDataInterface RawProbeEdit(ProbeInfo);
            RawProbeEdit.GetHeightDataFast(ProbeExtent.Min.X, ProbeExtent.Min.Y, ProbeExtent.Max.X, ProbeExtent.Max.Y,
                ProbeRaw.GetData(), ProbeWidth);
        }
    }
    const FTransform ProbeTransform = Landscape->LandscapeActorToWorld();
    auto RawBilinearZ = [&](double X, double Y, double& OutZ) -> bool
    {
        if (!bHaveRaw) return false;
        const FVector Local = ProbeTransform.InverseTransformPosition(FVector(X, Y, 0.0));
        const int32 X0 = FMath::FloorToInt(Local.X);
        const int32 Y0 = FMath::FloorToInt(Local.Y);
        if (X0 < ProbeExtent.Min.X || Y0 < ProbeExtent.Min.Y || X0 + 1 > ProbeExtent.Max.X || Y0 + 1 > ProbeExtent.Max.Y) return false;
        const double TX = Local.X - X0;
        const double TY = Local.Y - Y0;
        auto VZ = [&](int32 VX, int32 VY)
        {
            return ProbeTransform.TransformPosition(FVector(VX, VY,
                LandscapeDataAccess::GetLocalHeight(ProbeRaw[(VY - ProbeExtent.Min.Y) * ProbeWidth + VX - ProbeExtent.Min.X]))).Z;
        };
        OutZ = FMath::Lerp(FMath::Lerp(VZ(X0, Y0), VZ(X0 + 1, Y0), TX), FMath::Lerp(VZ(X0, Y0 + 1), VZ(X0 + 1, Y0 + 1), TX), TY);
        return true;
    };

    int32 ComplexMismatches = 0;
    int32 EditorMismatches = 0;
    for (FActorIterator RoadIt(World); RoadIt; ++RoadIt)
    {
        if (!RoadIt->GetActorLabel().StartsWith(TEXT("TOUR_FinalRoad_"))) continue;
        const FVector RoadCenter = RoadIt->GetActorLocation();
        const TOptional<float> ComplexHeight = Landscape->GetHeightAtLocation(FVector(RoadCenter.X, RoadCenter.Y, 0.0));
        const TOptional<float> EditorHeight = Landscape->GetHeightAtLocation(FVector(RoadCenter.X, RoadCenter.Y, 0.0), EHeightfieldSource::Editor);
        ++FreshGapSamples;
        if (!ComplexHeight.IsSet() || ComplexHeight.GetValue() <= WaterLevel)
        {
            ++FreshWaterSamples;
            continue;
        }
        const double Gap = RoadCenter.Z - ComplexHeight.GetValue();
        double RawZ = 0.0;
        const bool bHasRaw = RawBilinearZ(RoadCenter.X, RoadCenter.Y, RawZ);
        if (bHasRaw && ComplexHeight.IsSet() && FMath::Abs(ComplexHeight.GetValue() - RawZ) > 50.0) ++ComplexMismatches;
        if (bHasRaw && EditorHeight.IsSet() && FMath::Abs(EditorHeight.GetValue() - RawZ) > 50.0) ++EditorMismatches;
        if (Gap < FreshMinimumGap)
        {
            FreshMinimumGap = Gap;
            FreshMinimumActor = RoadIt->GetActorLabel();
        }
        if (Gap > FreshMaximumGap)
        {
            FreshMaximumGap = Gap;
            FreshMaximumActor = RoadIt->GetActorLabel();
        }
        if (Gap < 5.0 || Gap > 25.0)
        {
            UE_LOG(LogTemp, Display, TEXT("JPWATER_PROBE OUTLIER %s CENTER=(%.1f,%.1f) ROAD_Z=%.1f COMPLEX=%.1f EDITOR=%s RAW_BILINEAR=%.1f"),
                *RoadIt->GetActorLabel(), RoadCenter.X, RoadCenter.Y, RoadCenter.Z,
                ComplexHeight.GetValue(),
                EditorHeight.IsSet() ? *FString::Printf(TEXT("%.1f"), EditorHeight.GetValue()) : TEXT("NONE"),
                bHasRaw ? RawZ : -1.0);
        }
    }
    UE_LOG(LogTemp, Display, TEXT("JPWATER_PROBE FRESH_CLEARANCE SESSION=REGENERATED_COLLISION SAMPLES=%d MIN_GAP=%.3f (%s) MAX_GAP=%.3f (%s) WATER_SAMPLES=%d COMPLEX_VS_RAW_MISMATCHES=%d EDITOR_VS_RAW_MISMATCHES=%d"),
        FreshGapSamples,
        FreshGapSamples ? FreshMinimumGap : -1.0, *FreshMinimumActor,
        FreshGapSamples ? FreshMaximumGap : -1.0, *FreshMaximumActor,
        FreshWaterSamples, ComplexMismatches, EditorMismatches);
    UE_LOG(LogTemp, Display, TEXT("JPWATER_PROBE SUMMARY INTERVALS=%d WATER_SAMPLES=%d TOTAL_SAMPLES=%d GLOBAL_MIN_HEIGHT=%.1f"),
        IntervalCount, WaterSamples, NumPoints * SamplesPerSegment + 1, GlobalMinHeight);
    return true;
}

#else

bool UJPJurassicDreamLandscapeImportLibrary::ImportJurassicDreamTerrain()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::AssignTempMarkerFolders()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::SnapTempMarkersToLandscape()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::ProbeJP1993Heights(const FString& CsvPoints)
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::SpawnJP1993Markers(const FString& CsvPoints)
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::CreateTourRoadGuide()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::FixTourRoadGuideCentralRidge()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::EnhanceTourRoadVisualization()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::FixTourRoadCusps()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::FlattenTourRoadCuspsTangents()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::ProbeTourRoadWaterCrossing()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::FixTourRoadWaterCrossing()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::BuildTourRoadVisualPass()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::ProbeTourRoadGrading()
{
    return false;
}

bool UJPJurassicDreamLandscapeImportLibrary::GradeTourRoadLandscape()
{
    return false;
}

#endif
