import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { BaseHttpService } from '../core/base-http';
import { RolParticipante } from '../models/rol-participante.model';

@Injectable({
    providedIn: 'root'
})
export class RolesService extends BaseHttpService<RolParticipante> {
    protected baseUrl = 'http://localhost:8000/api/v1/roles-participante';

    constructor() {
        super(inject(HttpClient));
    }
}