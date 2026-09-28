export abstract class RolBase {
    codigo: string;
    nombre: string;
    descripcion: string;
    activo: boolean;
    creado_en?: string | Date;
    actualizado_en?: string | Date;

    constructor(data?: Partial<RolBase>) {
        this.codigo = data?.codigo || '';
        this.nombre = data?.nombre || '';
        this.descripcion = data?.descripcion || '';
        this.activo = data?.activo ?? true;
        this.creado_en = data?.creado_en;
        this.actualizado_en = data?.actualizado_en;
    }
}