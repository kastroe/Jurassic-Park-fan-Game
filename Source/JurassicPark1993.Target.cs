using UnrealBuildTool;
using System.Collections.Generic;

public class JurassicPark1993Target : TargetRules
{
    public JurassicPark1993Target(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("JurassicPark1993");
    }
}