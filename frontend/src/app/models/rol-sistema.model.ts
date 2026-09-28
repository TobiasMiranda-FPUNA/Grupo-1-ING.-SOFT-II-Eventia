import { RolBase } from "./base.model";

export class RolSistema extends RolBase {
    id_rol_sistema?: number;

    constructor(data?: Partial<RolSistema>) {
        super(data); // Envía los datos compartidos al constructor del padre
        this.id_rol_sistema = data?.id_rol_sistema;
    }
}