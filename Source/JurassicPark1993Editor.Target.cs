using UnrealBuildTool;
using System.Collections.Generic;

public class JurassicPark1993EditorTarget : TargetRules
{
    public JurassicPark1993EditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V7;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
        ExtraModuleNames.Add("JurassicPark1993");
    }
}