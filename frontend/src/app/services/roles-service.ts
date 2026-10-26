import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { BaseHttpService } from '../core/base-http';
import { RolParticipante } from '../models/rol-participante.model';
import { environment } from '../../environments/environment';

@Injectable({
    providedIn: 'root'
})
export class RolesService extends BaseHttpService<RolParticipante> {
    protected baseUrl = `${environment.apiUrl}/roles/participantes`;

    constructor() {
        super(inject(HttpClient));
    }
}