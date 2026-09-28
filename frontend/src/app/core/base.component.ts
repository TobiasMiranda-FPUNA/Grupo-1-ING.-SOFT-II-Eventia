export abstract class BaseComponent {
  // Variables públicas para que la vista (HTML) pueda leerlas sin errores
    isLoading = false;
    errorMessage: string | null = null;
    successMessage: string | null = null;

    // Métodos protegidos para que solo las clases hijas (TS) controlen el estado
    protected startLoading(): void {
        this.isLoading = true;
        this.clearMessages();
    }

    protected stopLoading(): void {
        this.isLoading = false;
    }

    protected clearMessages(): void {
        this.errorMessage = null;
        this.successMessage = null;
    }
}