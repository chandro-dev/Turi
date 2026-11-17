/* MODELO: reglas de negocio replicadas en el cliente para dar retroalimentacion inmediata.
   La fuente de verdad es el servidor (turnos-api/app/services/priority.py); aqui solo se refleja. */
export const PREGNANCY_MIN_AGE = 10;
export const PREGNANCY_MAX_AGE = 55;
export const MAX_AGE = 120;

export const pregnancyAllowed = (age) => Number.isInteger(age) && age >= PREGNANCY_MIN_AGE && age <= PREGNANCY_MAX_AGE;
export const PREGNANCY_HINT = `Gestante solo aplica entre ${PREGNANCY_MIN_AGE} y ${PREGNANCY_MAX_AGE} anos`;
