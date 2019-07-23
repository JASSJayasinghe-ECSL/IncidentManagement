import React from 'react';
import Dialog from '@material-ui/core/Dialog';
import { useSelector, useDispatch } from 'react-redux'

import { hideModal } from '../state/modal.actions'

import  ResponseTimeEditModal from './ResponseTimeEditModal';
import VerifyConfirmModal from './VerifyConfirmModal'
import EscalateModal from './EscalateModal';
import EscallateOutsideModal from './EscallateOutsideModal';

const MODAL_COMPONENTS = {
    'RESPOSE_TIME_EDIT': ResponseTimeEditModal,
    'VERIFY_CONFIRM_MODAL': VerifyConfirmModal,
    'ESCALATE_MODAL': EscalateModal,
    'ESCALLATE_OUTSIDE': EscallateOutsideModal
    /* other modals */
}

const RootModal = () => {
    // this retrieves props from the reducer
    const {modalType, modalProps} = useSelector(state => state.modalReducer)
    const dispatch = useDispatch()

    if (!modalType) {
        return null
    }

    const ModalContent = MODAL_COMPONENTS[modalType]

    return (
        <div>
            <Dialog
                open={modalType?true:false}
                onClose={()=>{dispatch(hideModal())}}
                aria-labelledby="form-dialog-title"
            >
                <ModalContent {...modalProps}/>
            </Dialog>
        </div>
    );
}

export default RootModal;
