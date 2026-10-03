import { RolBase } from './base.model';

export class RolParticipante extends RolBase {
    id?: number;

    constructor(data?: Partial<RolParticipante>) {
        super(data);
        this.id = data?.id;
    }
}