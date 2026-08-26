#include "JPDinosaurAI.h"

AJPDinosaurAI::AJPDinosaurAI()
{
    PrimaryActorTick.bCanEverTick = false;
}

void AJPDinosaurAI::SetAnimalState(EJPAnimalState NewState)
{
    State = NewState;
}
