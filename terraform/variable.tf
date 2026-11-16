locals {
    isprod = var.environment == "main"
    isdev  = var.environment == "develop" 

}
   
