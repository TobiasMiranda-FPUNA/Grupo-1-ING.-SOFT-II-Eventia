import { RolBase } from "./base.model";

export class RolParticipante extends RolBase {
    id_rol_participante?: number;
    en_uso: boolean;

    constructor(data?: Partial<RolParticipante>) {
        super(data);
        this.id_rol_participante = data?.id_rol_participante;
        this.en_uso = data?.en_uso ?? false;
    }

    desactivar(): void {
        this.activo = false;
    }
}