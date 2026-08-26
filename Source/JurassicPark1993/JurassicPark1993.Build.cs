using UnrealBuildTool;

public class JurassicPark1993 : ModuleRules
{
    public JurassicPark1993(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
            "AIModule", "GameplayTasks", "NavigationSystem", "Landscape", "Foliage"
        });

            if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.Add("UnrealEd");
            PrivateDependencyModuleNames.Add("RenderCore");
        }
    }
}
