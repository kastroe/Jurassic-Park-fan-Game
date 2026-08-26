#include "JPGameMode.h"
#include "JPPlayerCharacter.h"

AJPGameMode::AJPGameMode()
{
    DefaultPawnClass = AJPPlayerCharacter::StaticClass();
}
